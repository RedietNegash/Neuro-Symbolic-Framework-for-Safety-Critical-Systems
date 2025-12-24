# gold_standard.py
# Gold Standard Code for a Drone's Altitude Controller

def maintain_altitude(current_altitude: float) -> float:
    """
    Maintains a drone's altitude within the safe operating range of
    40 to 60 meters.
    """
    # The two core safety properties of the system are defined here as assertions.
    assert 40 <= current_altitude <= 60, "Altitude must be between 40 and 60 meters."
    
    # Corrective logic to ensure the altitude is always within the boundaries.
    if current_altitude < 40:
        print("Warning: Altitude is too low. Adjusting to 40 meters.")
        return 40.0
    elif current_altitude > 60:
        print("Warning: Altitude is too high. Adjusting to 60 meters.")
        return 60.0
    
    # If the altitude is already in the safe range, no change is needed.
    return current_altitude

def main():
    """
    Demonstrates the function with various test cases.
    """
    print("--- Testing Gold Standard Altitude Control Function ---")
    
    # Test Case 1: Altitude is within the safe range (50m)
    safe_altitude = 50.0
    print(f"\nInput: {safe_altitude}m. Expected output: {safe_altitude}m.")
    result = maintain_altitude(safe_altitude)
    print(f"Output: {result}m")
    
    # Test Case 2: Altitude is too low (35m)
    low_altitude = 35.0
    print(f"\nInput: {low_altitude}m. Expected output: 40.0m.")
    result = maintain_altitude(low_altitude)
    print(f"Output: {result}m")
    
    # Test Case 3: Altitude is too high (65m)
    high_altitude = 65.0
    print(f"\nInput: {high_altitude}m. Expected output: 60.0m.")
    result = maintain_altitude(high_altitude)
    print(f"Output: {result}m")

if __name__ == "__main__":
    main()
