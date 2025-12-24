class ArduPilotInterface:
    """
    Mocked deployment layer for future ArduPilot/SITL integration.
    All methods are stubs and clearly marked as inactive.
    """
    
    def __init__(self):
        print("[DEPLOYMENT LAYER] Initializing ArduPilot/SITL Mocked Interface...")
        self.active = False # Disabled by default

    def inject_mavlink_message(self, message_id: int, payload: dict):
        """Future hook for MAVLink message injection"""
        if not self.active:
            # print(f"[MOCK] Skipping MAVLink injection: {message_id}")
            pass
        else:
            # Real implementation would use pymavlink
            pass

    def bridge_ros2_topic(self, topic: str, data: any):
        """Future hook for ROS2 topic bridging"""
        if not self.active:
            # print(f"[MOCK] Skipping ROS2 bridge: {topic}")
            pass
        else:
            # Real implementation would use rclpy
            pass

    def trigger_failsafe(self, reason: str):
        """Standardized fail-safe trigger"""
        print(f"[DEPLOYMENT LAYER] FAIL-SAFE TRIGGERED: {reason}")
        # In future, this would send MAV_CMD_DO_SET_MODE (mode=RTL or LAND)
