#!/usr/bin/env python3
"""
Statistics Viewer - View detection statistics without running the monitoring system
"""

import sys
import json
from datetime import datetime
from detection_stats import DetectionStats, analyze_existing_detections

def show_menu():
    """Show the statistics menu"""
    print("\n" + "="*50)
    print("📊 AI MONITORING STATISTICS VIEWER")
    print("="*50)
    print("1. 📈 Current Session Summary")
    print("2. 🔍 Analyze All Detection Files")
    print("3. 📅 Recent Activity (Last 24 hours)")
    print("4. 🐦 Bird Species Report")
    print("5. 📊 Confidence Statistics")
    print("6. 🕐 Hourly Breakdown")
    print("7. 📋 Raw Statistics Data")
    print("8. 🧹 Reset Statistics")
    print("9. ❌ Exit")
    print("="*50)

def show_recent_activity(stats):
    """Show recent activity breakdown"""
    print("\n🕐 RECENT ACTIVITY (Last 24 Hours)")
    print("-" * 40)
    
    hourly = stats.get_hourly_breakdown(24)
    total_by_hour = {}
    
    for hour, counts in hourly.items():
        total = sum(counts.values())
        total_by_hour[hour] = total
    
    # Show hours with activity
    active_hours = [(hour, counts) for hour, counts in hourly.items() if sum(counts.values()) > 0]
    
    if active_hours:
        print("Active periods:")
        for hour, counts in sorted(active_hours, key=lambda x: x[0], reverse=True)[:12]:
            total = sum(counts.values())
            print(f"  {hour}: {counts['person']}👤 {counts['dog']}🐕 {counts['bird']}🐦 (Total: {total})")
    else:
        print("No activity in the last 24 hours")

def show_bird_species_report(stats):
    """Show detailed bird species report"""
    print("\n🐦 BIRD SPECIES REPORT")
    print("-" * 40)
    
    bird_species = dict(stats.stats['bird_species'])
    
    if bird_species:
        total_birds = sum(bird_species.values())
        print(f"Total bird detections: {total_birds}")
        print("Species breakdown:")
        
        for species, count in sorted(bird_species.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_birds) * 100
            print(f"  • {species}: {count} ({percentage:.1f}%)")
    else:
        print("No bird species detected yet")

def show_confidence_stats(stats):
    """Show confidence statistics"""
    print("\n📊 CONFIDENCE STATISTICS")
    print("-" * 40)
    
    averages = stats.get_confidence_averages()
    
    for obj_type, data in averages.items():
        if data['count'] > 0:
            print(f"{obj_type.upper()}:")
            print(f"  Average confidence: {data['average']:.2f}")
            print(f"  Range: {data['min']:.2f} - {data['max']:.2f}")
            print(f"  Total detections: {data['count']}")
            
            # Calculate confidence quality
            if data['average'] >= 0.8:
                quality = "Excellent 🌟"
            elif data['average'] >= 0.6:
                quality = "Good ✅"
            elif data['average'] >= 0.4:
                quality = "Fair ⚠️"
            else:
                quality = "Poor ❌"
            
            print(f"  Detection quality: {quality}")
            print()

def show_hourly_breakdown(stats):
    """Show detailed hourly breakdown"""
    print("\n🕐 HOURLY BREAKDOWN (Last 12 Hours)")
    print("-" * 50)
    
    hourly = stats.get_hourly_breakdown(12)
    
    print("Hour    | Person | Dog | Bird | Total")
    print("--------|--------|-----|------|------")
    
    for hour in sorted(hourly.keys(), reverse=True):
        counts = hourly[hour]
        total = sum(counts.values())
        print(f"{hour} |   {counts['person']:4d} | {counts['dog']:3d} |  {counts['bird']:3d} | {total:4d}")

def show_raw_data(stats):
    """Show raw statistics data"""
    print("\n📋 RAW STATISTICS DATA")
    print("-" * 40)
    
    print(f"Session start: {stats.stats['session_start']}")
    print(f"Total motion events: {stats.stats['total_motion_events']}")
    print(f"Total detections: {stats.stats['total_detections']}")
    print(f"Detection types: {dict(stats.stats['detections_by_type'])}")
    print(f"Recent detections: {len(stats.stats['detection_log'])}")
    
    if stats.stats['detection_log']:
        print("\nLast 5 detections:")
        for detection in stats.stats['detection_log'][-5:]:
            timestamp = detection['timestamp'][:19]  # Remove microseconds
            obj_type = detection['type']
            confidence = detection['confidence']
            species = detection.get('species', '')
            species_str = f" ({species})" if species else ""
            print(f"  {timestamp}: {obj_type}{species_str} - {confidence:.2f}")

def reset_statistics():
    """Reset all statistics"""
    print("\n🧹 RESET STATISTICS")
    print("-" * 30)
    
    confirm = input("Are you sure you want to reset all statistics? (yes/no): ").lower()
    
    if confirm == 'yes':
        try:
            import os
            if os.path.exists('detection_stats.json'):
                os.remove('detection_stats.json')
            print("✅ Statistics reset successfully!")
        except Exception as e:
            print(f"❌ Error resetting statistics: {e}")
    else:
        print("Reset cancelled.")

def main():
    """Main function"""
    while True:
        show_menu()
        
        try:
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == '9':
                print("Goodbye! 👋")
                break
            
            elif choice == '1':
                # Current session summary
                stats = DetectionStats()
                stats.print_summary()
            
            elif choice == '2':
                # Analyze all detection files
                stats = analyze_existing_detections()
                stats.print_summary()
            
            elif choice == '3':
                # Recent activity
                stats = DetectionStats()
                show_recent_activity(stats)
            
            elif choice == '4':
                # Bird species report
                stats = DetectionStats()
                show_bird_species_report(stats)
            
            elif choice == '5':
                # Confidence statistics
                stats = DetectionStats()
                show_confidence_stats(stats)
            
            elif choice == '6':
                # Hourly breakdown
                stats = DetectionStats()
                show_hourly_breakdown(stats)
            
            elif choice == '7':
                # Raw data
                stats = DetectionStats()
                show_raw_data(stats)
            
            elif choice == '8':
                # Reset statistics
                reset_statistics()
            
            else:
                print("Invalid choice. Please enter 1-9.")
            
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    # Allow command line usage too
    if len(sys.argv) > 1:
        stats = DetectionStats()
        
        if sys.argv[1] == 'summary':
            stats.print_summary()
        elif sys.argv[1] == 'analyze':
            stats = analyze_existing_detections()
            stats.print_summary()
        elif sys.argv[1] == 'live':
            stats.print_live_stats()
        else:
            print("Usage: python3 view_stats.py [summary|analyze|live]")
    else:
        main()