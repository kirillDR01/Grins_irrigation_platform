#!/usr/bin/env python3
"""List all phone numbers in Twilio account."""

from twilio.rest import Client

account_sid = 'AC746f6b24b3a0f5d6eba29bdbbe2a5a5b'
auth_token = 'df4b2e501c1b46c15587e9ffd6b23145'

client = Client(account_sid, auth_token)

print('Listing all phone numbers in account...')
print()

incoming_numbers = client.incoming_phone_numbers.list()

if incoming_numbers:
    print(f'Found {len(incoming_numbers)} phone number(s):')
    for number in incoming_numbers:
        print(f'  - {number.phone_number} (SID: {number.sid})')
        if number.capabilities:
            print(f'    SMS: {number.capabilities.get("sms", False)}, Voice: {number.capabilities.get("voice", False)}')
else:
    print('No phone numbers found in this account.')
    print('You need to purchase a phone number in the Twilio Console.')
    print('Visit: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming')
