"""Property-based tests for PollOption validation.

Validates: Scheduling Poll Req 1.1, 1.2, 1.3, 15.1
"""

from datetime import date, timedelta

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from pydantic import ValidationError

from grins_platform.schemas.campaign import CampaignCreate
from grins_platform.schemas.campaign_response import PollOption

# --- Strategies ---

_valid_key = st.sampled_from(["1", "2", "3", "4", "5"])
_valid_label = st.text(
    min_size=1,
    max_size=120,
    alphabet=st.characters(
        codec="utf-8",
        categories=("L", "N", "P", "Z"),
    ),
)
_date_st = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31),
)

_OPT_1 = {
    "key": "1",
    "label": "Week 1",
    "start_date": "2026-04-01",
    "end_date": "2026-04-07",
}
_OPT_3 = {
    "key": "3",
    "label": "Week 3",
    "start_date": "2026-04-15",
    "end_date": "2026-04-21",
}


@st.composite
def valid_poll_option(draw: st.DrawFn) -> dict[str, str]:
    key = draw(_valid_key)
    label = draw(_valid_label)
    start = draw(_date_st)
    delta = draw(st.integers(min_value=0, max_value=365))
    end = start + timedelta(days=delta)
    return {
        "key": key,
        "label": label,
        "start_date": str(start),
        "end_date": str(end),
    }


@st.composite
def valid_poll_options_list(draw: st.DrawFn) -> list[dict[str, str]]:
    count = draw(st.integers(min_value=2, max_value=5))
    options = []
    for i in range(1, count + 1):
        opt = draw(valid_poll_option())
        opt["key"] = str(i)
        options.append(opt)
    return options


# --- Property 1: PollOption validation round-trip ---


@pytest.mark.unit
class TestPollOptionProperties:
    @given(data=valid_poll_option())
    @settings(max_examples=50)
    def test_valid_poll_option_round_trips_through_json(
        self,
        data: dict[str, str],
    ) -> None:
        """Valid PollOptions round-trip through JSON."""
        opt = PollOption(**data)
        serialized = opt.model_dump_json()
        restored = PollOption.model_validate_json(serialized)
        assert restored.key == opt.key
        assert restored.label == opt.label
        assert restored.start_date == opt.start_date
        assert restored.end_date == opt.end_date

    @given(
        start=_date_st,
        gap=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=30)
    def test_end_date_before_start_date_rejected(
        self,
        start: date,
        gap: int,
    ) -> None:
        """end_date < start_date is always rejected."""
        end = start - timedelta(days=gap)
        with pytest.raises(
            ValidationError,
            match="end_date must be >= start_date",
        ):
            PollOption(
                key="1",
                label="Test",
                start_date=start,
                end_date=end,
            )

    @given(options=valid_poll_options_list())
    @settings(max_examples=30)
    def test_valid_list_has_sequential_keys(
        self,
        options: list[dict[str, str]],
    ) -> None:
        """Valid lists have sequential keys starting from '1'."""
        parsed = [PollOption(**o) for o in options]
        assert 2 <= len(parsed) <= 5
        for i, opt in enumerate(parsed, 1):
            assert opt.key == str(i)

    def test_single_option_rejected(self) -> None:
        """A list with only 1 option is rejected."""
        with pytest.raises(
            ValidationError,
            match="2-5 entries",
        ):
            CampaignCreate(
                name="Test",
                campaign_type="sms",
                body="Hello",
                poll_options=[_OPT_1],
            )

    def test_six_options_rejected(self) -> None:
        """A list with 6 options is rejected."""
        opts = [
            {
                "key": str(i),
                "label": f"Week {i}",
                "start_date": "2026-04-01",
                "end_date": "2026-04-07",
            }
            for i in range(1, 7)
        ]
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="Test",
                campaign_type="sms",
                body="Hello",
                poll_options=opts,
            )

    def test_non_sequential_keys_rejected(self) -> None:
        """Keys like ['1', '3'] are rejected."""
        with pytest.raises(
            ValidationError,
            match="sequential",
        ):
            CampaignCreate(
                name="Test",
                campaign_type="sms",
                body="Hello",
                poll_options=[_OPT_1, _OPT_3],
            )
