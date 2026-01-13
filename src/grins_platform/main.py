#!/usr/bin/env python3
"""
MyPy Configuration Test Script

This script demonstrates and tests various MyPy type checking features
optimized for AI-generated code patterns. It includes examples of:
- Strict type checking
- Generic types and type variables
- Protocol definitions
- Union types and Optional handling
- Class inheritance and method overriding
- Error handling patterns
- AI-friendly type patterns
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
    overload,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for generic programming
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
SerializableT = TypeVar("SerializableT", bound="Serializable")


class ProcessingStatus(Enum):
    """Status enumeration for processing operations."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult(Generic[T]):
    """Generic result container for processing operations."""
    
    status: ProcessingStatus
    data: Optional[T]
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        """Initialize default metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class Serializable(Protocol):
    """Protocol for objects that can be serialized to JSON."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Serializable":
        """Create object from dictionary representation."""
        ...


class DataProcessor(ABC, Generic[T]):
    """Abstract base class for data processors with generic type support."""
    
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        """Initialize the processor with name and configuration.
        
        Args:
            name: Processor name for identification
            config: Configuration dictionary
        """
        super().__init__()
        self.name = name
        self.config = config
        self._processed_count = 0
    
    @property
    def processed_count(self) -> int:
        """Get the number of processed items."""
        return self._processed_count
    
    @abstractmethod
    def process_item(self, item: T) -> ProcessingResult[T]:
        """Process a single item.
        
        Args:
            item: Item to process
            
        Returns:
            Processing result with status and data
        """
        ...
    
    def process_batch(self, items: List[T]) -> List[ProcessingResult[T]]:
        """Process a batch of items.
        
        Args:
            items: List of items to process
            
        Returns:
            List of processing results
        """
        results: List[ProcessingResult[T]] = []
        
        for item in items:
            try:
                result = self.process_item(item)
                results.append(result)
                if result.status == ProcessingStatus.COMPLETED:
                    self._processed_count += 1
            except Exception as e:
                error_result = ProcessingResult[T](
                    status=ProcessingStatus.FAILED,
                    data=None,
                    error_message=str(e),
                )
                results.append(error_result)
        
        return results


class StringProcessor(DataProcessor[str]):
    """Concrete implementation of DataProcessor for string processing."""
    
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        """Initialize string processor."""
        super().__init__(name, config)
        self.min_length: int = config.get("min_length", 1)
        self.max_length: int = config.get("max_length", 1000)
    
    def process_item(self, item: str) -> ProcessingResult[str]:
        """Process a single string item.
        
        Args:
            item: String to process
            
        Returns:
            Processing result with processed string
        """
        # Validate length constraints
        if len(item) < self.min_length:
            return ProcessingResult[str](
                status=ProcessingStatus.FAILED,
                data=None,
                error_message=f"String too short: {len(item)} < {self.min_length}",
            )
        elif len(item) > self.max_length:
            return ProcessingResult[str](
                status=ProcessingStatus.FAILED,
                data=None,
                error_message=f"String too long: {len(item)} > {self.max_length}",
            )
        
        # Process the string (normalize and clean)
        processed = item.strip().lower().title()
        
        return ProcessingResult[str](
            status=ProcessingStatus.COMPLETED,
            data=processed,
            metadata={"original_length": len(item), "processed_length": len(processed)},
        )


@dataclass
class User(Serializable):
    """User data class implementing Serializable protocol."""
    
    id: int
    name: str
    email: str
    active: bool = True
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "active": self.active,
            "metadata": self.metadata or {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary representation."""
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            active=data.get("active", True),
            metadata=data.get("metadata"),
        )


class FileManager(Generic[SerializableT]):
    """Generic file manager for serializable objects."""
    
    def __init__(self, file_path: Path) -> None:
        """Initialize file manager with path."""
        super().__init__()
        self.file_path = file_path
    
    @overload
    def save_data(self, data: List[Serializable]) -> bool:
        ...
    
    @overload
    def save_data(self, data: Serializable) -> bool:
        ...
    
    def save_data(self, data: Union[Serializable, List[Serializable]]) -> bool:
        """Save serializable data to file.
        
        Args:
            data: Single object or list of objects to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(data, list):
                json_data: Union[Dict[str, Any], List[Dict[str, Any]]] = [item.to_dict() for item in data]
            else:
                json_data = data.to_dict()
            
            with self.file_path.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            return True
        
        except Exception as e:
            logger.error("Failed to save data: %s", e)
            return False
    
    def load_data(self, data_class: type[SerializableT]) -> Optional[List[SerializableT]]:
        """Load data from file.
        
        Args:
            data_class: Class constructor for creating objects from dict
            
        Returns:
            List of loaded objects or None if failed
        """
        try:
            if not self.file_path.exists():
                return None
            
            with self.file_path.open("r", encoding="utf-8") as f:
                json_data: Union[Dict[str, Any], List[Dict[str, Any]]] = json.load(f)
            
            if isinstance(json_data, list):
                return [cast(SerializableT, data_class.from_dict(item)) for item in json_data]
            else:
                return [cast(SerializableT, data_class.from_dict(json_data))]
        
        except Exception as e:
            logger.error("Failed to load data: %s", e)
            return None


def process_users_with_validation(
    users: List[User],
    processor: DataProcessor[str],
) -> Dict[str, Union[int, float, List[str]]]:
    """Process user names with validation and return statistics.
    
    Args:
        users: List of users to process
        processor: String processor for name validation
        
    Returns:
        Dictionary with processing statistics and results
    """
    names = [user.name for user in users]
    results = processor.process_batch(names)
    
    successful_results: List[str] = []
    failed_results: List[str] = []
    
    for result in results:
        if result.status == ProcessingStatus.COMPLETED and result.data is not None:
            successful_results.append(result.data)
        else:
            failed_results.append(result.error_message or "Unknown error")
    
    return {
        "total_processed": len(results),
        "successful": len(successful_results),
        "failed": len(failed_results),
        "success_rate": len(successful_results) / len(results) if results else 0.0,
        "successful_names": successful_results,
        "error_messages": failed_results,
    }


def demonstrate_type_narrowing(value: Union[str, int, None]) -> str:
    """Demonstrate type narrowing with Union types.
    
    Args:
        value: Value that could be string, int, or None
        
    Returns:
        String representation of the value
    """
    if value is None:
        return "None"
    elif isinstance(value, str):
        # MyPy knows value is str here
        return f"String: {value.upper()}"
    else:
        # MyPy knows value is int here (only remaining type)
        return f"Integer: {value * 2}"


def main() -> int:
    """Main function demonstrating MyPy type checking features.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("🔍 Testing MyPy Configuration for AI-Generated Code")
    print("=" * 60)
    
    # Test generic data processing
    config = {"min_length": 2, "max_length": 50}
    processor = StringProcessor("name_processor", config)
    
    # Create test users
    users = [
        User(1, "Alice Smith", "alice@example.com"),
        User(2, "Bob Jones", "bob@example.com"),
        User(3, "", "invalid@example.com"),  # Invalid name (too short)
        User(4, "Charlie Brown", "charlie@example.com"),
    ]
    
    # Process users
    stats = process_users_with_validation(users, processor)
    
    print("📊 Processing Results:")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Successful: {stats['successful']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    
    # Test file operations
    file_manager: FileManager[User] = FileManager(Path("output/users.json"))
    
    # Use cast to handle the variance issue with List[User] -> List[Serializable]
    if file_manager.save_data(cast(List[Serializable], users)):
        print("✅ Users saved to file successfully")
    else:
        print("❌ Failed to save users to file")
    
    # Test type narrowing
    test_values: List[Union[str, int, None]] = ["hello", 42, None]
    
    print("\n🔧 Type Narrowing Examples:")
    for value in test_values:
        result = demonstrate_type_narrowing(value)
        print(f"   {result}")
    
    # Test explicit Any usage (allowed in our config)
    dynamic_data: Any = {"key": "value", "number": 123}
    processed_dynamic = cast(Dict[str, Union[str, int]], dynamic_data)
    
    print(f"\n📝 Dynamic data processing: {processed_dynamic}")
    
    print("\n✅ MyPy type checking demonstration completed!")
    print("   • Strict type checking enabled")
    print("   • Generic types and protocols working")
    print("   • Union type narrowing functional")
    print("   • Error handling patterns validated")
    print("   • AI-friendly patterns supported")
    
    return 0


if __name__ == "__main__":
    exit(main())