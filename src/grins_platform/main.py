#!/usr/bin/env python3
"""
Main script to demonstrate Ruff configuration optimized for AI self-correction.

This script intentionally contains various code patterns that Ruff will analyze
and potentially fix, demonstrating the comprehensive rule set configured for
AI-generated code improvement.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Example class demonstrating various code patterns for Ruff analysis."""

    def __init__(self, config_path: str, debug: bool = False):
        """Initialize the data processor.

        Args:
            config_path: Path to configuration file
            debug: Enable debug mode
        """
        self.config_path = Path(config_path)
        self.debug = debug
        self.data: List[Dict[str, Union[str, int, float]]] = []

    def load_config(self) -> Dict[str, str]:
        """Load configuration from file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise

    def process_data(self, input_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Process input data with various transformations.

        Args:
            input_data: List of data dictionaries to process

        Returns:
            Processed data list
        """
        processed = []

        for item in input_data:
            # Demonstrate various code patterns
            if item.get("name"):
                # String processing
                name = item["name"].strip().lower()

                # Conditional logic
                if len(name) > 0:
                    processed_item = {
                        "name": name.title(),
                        "processed": True,
                        "length": len(name),
                    }

                    # Add optional fields
                    if "category" in item:
                        processed_item["category"] = item["category"]

                    processed.append(processed_item)

        return processed

    def save_results(self, data: List[Dict[str, str]], output_path: str) -> bool:
        """Save processed results to file.

        Args:
            data: Data to save
            output_path: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Results saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return False

    def run_analysis(self) -> Optional[Dict[str, int]]:
        """Run data analysis and return statistics.

        Returns:
            Analysis statistics or None if no data
        """
        if not self.data:
            logger.warning("No data available for analysis")
            return None

        stats = {
            "total_items": len(self.data),
            "processed_items": sum(
                1 for item in self.data if item.get("processed", False)
            ),
            "average_length": sum(item.get("length", 0) for item in self.data)
            / len(self.data),
        }

        return stats


def validate_environment() -> bool:
    """Validate that the environment is properly configured.

    Returns:
        True if environment is valid, False otherwise
    """
    required_vars = ["HOME", "PATH"]

    for var in required_vars:
        if var not in os.environ:
            logger.error(f"Required environment variable missing: {var}")
            return False

    return True


def run_ruff_check() -> bool:
    """Run Ruff check on the current file to demonstrate self-correction.

    Returns:
        True if Ruff check passes, False otherwise
    """
    try:
        # Run Ruff check
        result = subprocess.run(
            ["ruff", "check", "main.py", "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info("Ruff check passed - no issues found!")
            return True
        # Parse and display issues
        if result.stdout:
            try:
                issues = json.loads(result.stdout)
                logger.warning(f"Ruff found {len(issues)} issues:")
                for issue in issues[:5]:  # Show first 5 issues
                    logger.warning(
                        f"  {issue.get('code', 'Unknown')}: {issue.get('message', 'No message')}",
                    )
            except json.JSONDecodeError:
                logger.warning(f"Ruff output: {result.stdout}")
        return False

    except subprocess.TimeoutExpired:
        logger.error("Ruff check timed out")
        return False
    except FileNotFoundError:
        logger.error("Ruff not found - please install ruff")
        return False
    except Exception as e:
        logger.error(f"Error running Ruff check: {e}")
        return False


def run_ruff_format() -> bool:
    """Run Ruff format on the current file to demonstrate auto-formatting.

    Returns:
        True if formatting succeeds, False otherwise
    """
    try:
        result = subprocess.run(
            ["ruff", "format", "main.py", "--check"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            logger.info("File is properly formatted!")
            return True
        logger.info("File needs formatting - run 'ruff format main.py' to fix")
        return False

    except Exception as e:
        logger.error(f"Error running Ruff format: {e}")
        return False


def main() -> int:
    """Main function demonstrating Ruff configuration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🔍 Testing Ruff Configuration for AI Self-Correction")
    print("=" * 60)

    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed")
        return 1

    # Create sample data
    sample_data = [
        {"name": "  Alice Smith  ", "category": "user"},
        {"name": "bob jones", "category": "admin"},
        {"name": "", "category": "guest"},  # This will be filtered out
        {"name": "Charlie Brown", "category": "user"},
    ]

    # Initialize processor
    try:
        # Create a temporary config file
        config_path = Path("temp_config.json")
        config_data = {
            "debug": True,
            "output_format": "json",
            "max_items": 100,
        }

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        processor = DataProcessor(str(config_path), debug=True)

        # Process data
        processed_data = processor.process_data(sample_data)
        processor.data = processed_data

        # Run analysis
        stats = processor.run_analysis()
        if stats:
            print("📊 Analysis Results:")
            print(f"   Total items: {stats['total_items']}")
            print(f"   Processed items: {stats['processed_items']}")
            print(f"   Average length: {stats['average_length']:.1f}")

        # Save results
        output_path = "output/results.json"
        success = processor.save_results(processed_data, output_path)

        if success:
            print(f"✅ Results saved to {output_path}")
        else:
            print("❌ Failed to save results")

        # Clean up
        config_path.unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return 1

    print("\n🔧 Running Ruff Analysis:")
    print("-" * 30)

    # Test Ruff check
    check_passed = run_ruff_check()
    format_ok = run_ruff_format()

    if check_passed and format_ok:
        print("✅ All Ruff checks passed!")
    else:
        print(
            "⚠️  Some Ruff issues found - this demonstrates the self-correction capabilities",
        )

    print("\n📝 Ruff Configuration Summary:")
    print("   • Comprehensive rule set for AI-generated code")
    print("   • Automatic fixing enabled for most rules")
    print("   • Optimized for code quality and consistency")
    print("   • Security and performance checks included")

    return 0


if __name__ == "__main__":
    sys.exit(main())
