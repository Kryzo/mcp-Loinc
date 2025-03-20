import argparse
import json
from sncf_server import initialize_csv_station_finder, initialize_sncf_api, check_disruptions

def main():
    parser = argparse.ArgumentParser(description="SNCF Disruption Debugger")
    parser.add_argument('--api-key', required=True, help='API Key for SNCF')
    parser.add_argument('--count', type=int, default=3, help='Maximum number of disruptions to return')
    parser.add_argument('--station-id', help='Filter disruptions affecting a specific station')
    parser.add_argument('--line-id', help='Filter disruptions affecting a specific line')
    parser.add_argument('--since', help='Only disruptions valid after this date (format YYYYMMDDTHHMMSS)')
    parser.add_argument('--until', help='Only disruptions valid before this date (format YYYYMMDDTHHMMSS)')
    parser.add_argument('--output', default='disruption_data.json', help='Output file for raw disruption data')
    args = parser.parse_args()

    # Initialize the global variables in sncf_server
    import sncf_server
    
    # Initialize CSV station finder
    csv_path = 'train_stations_europe.csv'
    csv_finder = initialize_csv_station_finder(csv_path)
    sncf_server.csv_station_finder = csv_finder
    
    # Initialize SNCF API
    sncf_api_instance = initialize_sncf_api(args.api_key)
    sncf_server.sncf_api = sncf_api_instance
    
    # Check for disruptions with debug mode enabled
    disruption_params = {
        'count': args.count,
        'debug': True
    }
    
    if args.station_id:
        disruption_params['station_id'] = args.station_id
    
    if args.line_id:
        disruption_params['line_id'] = args.line_id
    
    if args.since:
        disruption_params['since'] = args.since
    
    if args.until:
        disruption_params['until'] = args.until
    
    print(f"Retrieving {args.count} disruptions in debug mode...")
    result = check_disruptions(**disruption_params)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Retrieved {result['count']} disruptions")
        
        # Save the raw disruption data to a file for analysis
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result['raw_disruptions'], f, indent=2, ensure_ascii=False)
        
        print(f"Raw disruption data saved to {args.output}")
        
        # Print a summary of the first disruption to see its structure
        if result['count'] > 0:
            first_disruption = result['raw_disruptions'][0]
            print("\nFirst disruption structure:")
            print(f"ID: {first_disruption.get('id', 'N/A')}")
            print(f"Status: {first_disruption.get('status', 'N/A')}")
            print(f"Severity: {first_disruption.get('severity', {}).get('name', 'N/A')}")
            
            # Check for key structures we're interested in
            print("\nKey structures present:")
            for key in ['impacted_objects', 'impacted_stops', 'impacted_sections', 'vehicle_journey']:
                if key in first_disruption:
                    print(f"- {key}: Yes ({len(first_disruption[key]) if isinstance(first_disruption[key], list) else 'Object'})")
                else:
                    print(f"- {key}: No")
            
            # Check for messages
            if 'messages' in first_disruption and first_disruption['messages']:
                print(f"\nSample message: {first_disruption['messages'][0].get('text', 'N/A')}")

if __name__ == "__main__":
    main()
