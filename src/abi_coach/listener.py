"""Backward compatibility shim for abi_coach.listener."""

from abi_coach.core.audio.listener import AudioListener, ListenerConfig, play_beep, VK_MAP

__all__ = ["AudioListener", "ListenerConfig", "play_beep", "VK_MAP"]
