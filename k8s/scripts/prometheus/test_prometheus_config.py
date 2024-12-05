#!/usr/bin/env python3

from config_prometheus import PrometheusConfig
import time

def test_rule_updates():
    config = PrometheusConfig()

    # Test different thresholds
    thresholds = [100, 300, 500]
    windows = ['10s', '30s']
    
    for threshold in thresholds:
        for window in windows:
            print(f"\nTesting update with threshold={threshold}ms, window={window}")
            try:
                
                # Actually apply the changes
                print("\nApplying changes...")
                config.update_rules(
                    latency_threshold=threshold,
                    evaluation_window=window
                )
                
                # Wait for changes to apply
                print("Waiting for changes to propagate...")
                time.sleep(10)
                
                # Get and verify new rules
                print("\nVerifying new values were applied:")
                new_rules = config.get_current_rules()
                
                # Extract and check the relevant rules
                http_rule = new_rules['groups'][0]['rules'][0]
                rpc_rule = new_rules['groups'][1]['rules'][0] 
                critical_rule = new_rules['groups'][2]['rules'][0]
                
                print(f"HTTP Latency Rule:")
                print(f"- Threshold: {threshold} (in expression: {http_rule['expr']})")
                print(f"- Window: {window} (in rule: {http_rule['for']})")
                
                print(f"\nRPC Latency Rule:")
                print(f"- Threshold: {threshold} (in expression: {rpc_rule['expr']})")
                print(f"- Window: {window} (in rule: {rpc_rule['for']})")
                
                print(f"\nCritical Service Rule:")
                print(f"- Threshold: {threshold} (in expression: {critical_rule['expr']})")
                print(f"- Window: {window} (in rule: {critical_rule['for']})")
                
            except Exception as e:
                print(f"Error during test: {e}")
            
            print("\n" + "="*80 + "\n")
            
            # Wait between tests
            time.sleep(5)

if __name__ == "__main__":
    test_rule_updates() 