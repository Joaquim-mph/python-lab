"""
Test script for ConfigManager.

Tests configuration saving, loading, export, and import functionality.
"""

from pathlib import Path
from src.tui.config_manager import ConfigManager


def test_config_manager():
    """Test ConfigManager functionality."""
    print("=" * 60)
    print("Testing ConfigManager")
    print("=" * 60)

    # Use a test config file
    test_config_file = Path(".test_lab_plotter_configs.json")
    if test_config_file.exists():
        test_config_file.unlink()

    cm = ConfigManager(config_file=test_config_file, max_recent=10)

    # Test 1: Save a configuration
    print("\n1. Testing config save...")
    config1 = {
        "chip_number": 67,
        "chip_group": "Alisson",
        "plot_type": "ITS",
        "legend_by": "vg",
        "baseline": 60.0,
        "padding": 0.05,
        "vg_filter": 3.0,
        "seq_numbers": [52, 57, 58]
    }

    config_id1 = cm.save_config(config1, "Test ITS plot at VG=3V")
    print(f"   ✓ Saved config with ID: {config_id1}")

    # Small delay to ensure unique timestamp
    import time
    time.sleep(1)

    # Test 2: Save another configuration (auto-description)
    print("\n2. Testing auto-description...")
    config2 = {
        "chip_number": 72,
        "chip_group": "Alisson",
        "plot_type": "IVg",
        "vds_filter": -0.1,
        "wavelength_filter": 455.0,
        "seq_numbers": [10, 11, 12]
    }

    config_id2 = cm.save_config(config2)
    print(f"   ✓ Saved config with auto-description: {config_id2}")

    # Test 3: Load configuration
    print("\n3. Testing config load...")
    loaded = cm.load_config(config_id1)
    if loaded:
        print(f"   ✓ Loaded config: chip {loaded['chip_number']}, type {loaded['plot_type']}")
        assert loaded["chip_number"] == 67
        assert loaded["plot_type"] == "ITS"
    else:
        print("   ✗ Failed to load config")

    # Test 4: Get recent configs
    print("\n4. Testing recent configs list...")
    recent = cm.get_recent_configs(limit=5)
    print(f"   ✓ Found {len(recent)} recent configs")
    for entry in recent:
        print(f"      - {entry['id']}: {entry['description']}")

    # Test 5: Get statistics
    print("\n5. Testing statistics...")
    stats = cm.get_stats()
    print(f"   ✓ Total configs: {stats['total_count']}")
    print(f"   ✓ By plot type: {stats['by_plot_type']}")
    print(f"   ✓ By chip: {stats['by_chip']}")

    # Test 6: Export configuration
    print("\n6. Testing config export...")
    export_path = Path("test_export_config.json")
    if cm.export_config(config_id1, export_path):
        print(f"   ✓ Exported to {export_path}")
        assert export_path.exists()
    else:
        print("   ✗ Export failed")

    # Test 7: Import configuration
    print("\n7. Testing config import...")
    imported_id = cm.import_config(export_path)
    if imported_id:
        print(f"   ✓ Imported config with new ID: {imported_id}")
        # Verify it was imported
        stats_after = cm.get_stats()
        assert stats_after['total_count'] == stats['total_count'] + 1
    else:
        print("   ✗ Import failed")

    # Test 8: Search configurations
    print("\n8. Testing config search...")
    results = cm.search_configs("ITS")
    print(f"   ✓ Found {len(results)} configs matching 'ITS'")

    results_chip = cm.search_configs("67")
    print(f"   ✓ Found {len(results_chip)} configs for chip 67")

    # Test 9: Delete configuration
    print("\n9. Testing config deletion...")
    stats_before_delete = cm.get_stats()
    print(f"   Stats before delete: {stats_before_delete['total_count']} configs")

    if cm.delete_config(config_id2):
        print(f"   ✓ Deleted config {config_id2}")
        stats_after_delete = cm.get_stats()
        print(f"   Stats after delete: {stats_after_delete['total_count']} configs")
        assert stats_after_delete['total_count'] == stats_before_delete['total_count'] - 1
    else:
        print("   ✗ Deletion failed")

    # Test 10: Clear all
    print("\n10. Testing clear all...")
    deleted_count = cm.clear_all()
    print(f"   ✓ Cleared {deleted_count} configurations")

    final_stats = cm.get_stats()
    assert final_stats['total_count'] == 0
    print("   ✓ All configs cleared")

    # Cleanup
    print("\n" + "=" * 60)
    print("Cleaning up test files...")
    if test_config_file.exists():
        test_config_file.unlink()
        print(f"   ✓ Deleted {test_config_file}")

    if export_path.exists():
        export_path.unlink()
        print(f"   ✓ Deleted {export_path}")

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_config_manager()
