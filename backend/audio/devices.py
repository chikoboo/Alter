"""Alter - オーディオデバイス列挙

Windows WASAPI経由でマイク・スピーカーデバイスを列挙する。
Linux環境では空のリストを返す（開発用フォールバック）。
"""

import sys
from dataclasses import dataclass


@dataclass
class AudioDevice:
    """オーディオデバイス情報"""
    index: int
    name: str
    is_input: bool  # True=マイク, False=スピーカー
    is_loopback: bool
    channels: int
    default_sample_rate: float


def list_audio_devices() -> list[AudioDevice]:
    """利用可能なオーディオデバイスを列挙する"""
    if sys.platform != "win32":
        print("[WARNING] WASAPI はWindows専用です。ダミーデバイスを返します。")
        return _get_dummy_devices()

    return _list_wasapi_devices()


def _list_wasapi_devices() -> list[AudioDevice]:
    """WASAPIデバイスを列挙（Windows専用）"""
    try:
        import pyaudiowpatch as pyaudio  # type: ignore
    except ImportError:
        print("[ERROR] pyaudiowpatch がインストールされていません")
        return []

    devices: list[AudioDevice] = []
    p = pyaudio.PyAudio()

    try:
        # WASAPIホストAPIのインデックスを取得
        wasapi_info = None
        for i in range(p.get_host_api_count()):
            api_info = p.get_host_api_info_by_index(i)
            if api_info.get("name", "").lower().find("wasapi") >= 0:
                wasapi_info = api_info
                break

        if wasapi_info is None:
            print("[ERROR] WASAPI ホストAPIが見つかりません")
            return []

        # デバイスを列挙
        for i in range(p.get_device_count()):
            try:
                dev_info = p.get_device_info_by_index(i)
                if dev_info.get("hostApi") != wasapi_info.get("index"):
                    continue

                is_input = dev_info.get("maxInputChannels", 0) > 0
                is_output = dev_info.get("maxOutputChannels", 0) > 0
                is_loopback = dev_info.get("isLoopbackDevice", False)

                # 入力デバイス（マイク）
                if is_input and not is_loopback:
                    devices.append(AudioDevice(
                        index=i,
                        name=dev_info.get("name", f"Device {i}"),
                        is_input=True,
                        is_loopback=False,
                        channels=dev_info.get("maxInputChannels", 1),
                        default_sample_rate=dev_info.get("defaultSampleRate", 16000.0),
                    ))

                # ループバックデバイス（スピーカー出力のキャプチャ）
                if is_loopback:
                    devices.append(AudioDevice(
                        index=i,
                        name=dev_info.get("name", f"Device {i}"),
                        is_input=False,
                        is_loopback=True,
                        channels=dev_info.get("maxInputChannels", 2),
                        default_sample_rate=dev_info.get("defaultSampleRate", 16000.0),
                    ))

            except Exception as e:
                print(f"[WARNING] デバイス {i} の情報取得に失敗: {e}")
                continue

    finally:
        p.terminate()

    return devices


def get_microphone_devices() -> list[AudioDevice]:
    """マイクデバイスのみを返す"""
    return [d for d in list_audio_devices() if d.is_input and not d.is_loopback]


def get_loopback_devices() -> list[AudioDevice]:
    """ループバックデバイス（スピーカー出力キャプチャ用）のみを返す"""
    return [d for d in list_audio_devices() if d.is_loopback]


def _get_dummy_devices() -> list[AudioDevice]:
    """Linux開発環境向けダミーデバイス"""
    return [
        AudioDevice(0, "ダミーマイク (開発用)", True, False, 1, 16000.0),
        AudioDevice(1, "ダミースピーカー (開発用)", False, True, 2, 16000.0),
    ]
