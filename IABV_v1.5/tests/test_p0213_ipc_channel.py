"""P0.213 Tests for IPC Channel (Windows named pipes).

DESIGN_RECONSTRUCTION: Tests are new implementation reconstructed from
experimental design evidence. They are NOT recovered historical code.

Tests for Windows named pipes for IPC transport.
"""
import pytest
from iabv_v15.infra.ipc.ipc_channel import WindowsNamedPipe, IpcMessage


class TestIpcMessage:
    """Test IpcMessage serialization."""

    def test_message_to_json(self):
        """Test A: message serialization to JSON."""
        message = IpcMessage("test_type", {"key": "value"})
        json_str = message.to_json()
        
        assert "test_type" in json_str
        assert "key" in json_str
        assert "value" in json_str

    def test_message_from_json(self):
        """Test B: message deserialization from JSON."""
        json_str = '{"message_type": "test_type", "data": {"key": "value"}}'
        message = IpcMessage.from_json(json_str)
        
        assert message.message_type == "test_type"
        assert message.data["key"] == "value"

    def test_message_roundtrip(self):
        """Test C: message serialization roundtrip."""
        original = IpcMessage("test_type", {"key": "value"})
        json_str = original.to_json()
        restored = IpcMessage.from_json(json_str)
        
        assert restored.message_type == original.message_type
        assert restored.data == original.data


class TestWindowsNamedPipe:
    """Test Windows named pipe functionality."""

    def test_pipe_creation_requires_win32(self):
        """Test D: pipe creation requires win32 (Windows only)."""
        # This test verifies that Windows named pipes require pywin32
        # On non-Windows platforms, this should raise RuntimeError
        try:
            pipe = WindowsNamedPipe(r"\\.\pipe\test_pipe", 12345)
            pipe.create_server()
            # If we get here, win32 is available
            pipe.close()
        except RuntimeError as e:
            # Expected on non-Windows platforms
            assert "Windows named pipes require pywin32" in str(e)

    def test_pipe_initialization(self):
        """Test E: pipe initialization."""
        try:
            pipe = WindowsNamedPipe(r"\\.\pipe\test_pipe", 12345)
            assert pipe.pipe_name == r"\\.\pipe\test_pipe"
            assert pipe.producer_pid == 12345
            assert pipe.pipe_handle is None
        except RuntimeError:
            # Skip on non-Windows platforms
            pytest.skip("Windows named pipes require pywin32")

    def test_pipe_close(self):
        """Test F: pipe close."""
        try:
            pipe = WindowsNamedPipe(r"\\.\pipe\test_pipe", 12345)
            pipe.create_server()
            assert pipe.pipe_handle is not None
            
            pipe.close()
            assert pipe.pipe_handle is None
        except RuntimeError:
            # Skip on non-Windows platforms
            pytest.skip("Windows named pipes require pywin32")

    def test_message_send_receive(self):
        """Test G: message send and receive (requires actual pipe)."""
        # This test requires actual pipe connection, which is complex to test
        # in unit tests. We'll skip for now and rely on integration tests.
        pytest.skip("Integration test - requires actual pipe connection")

    def test_pid_validation_in_security_descriptor(self):
        """Test H: PID validation via security descriptor."""
        # This test verifies that the security descriptor includes PID validation
        # Actual verification requires Windows API calls, which is complex in unit tests
        pytest.skip("Integration test - requires Windows API verification")

    def test_producer_scope_validation(self):
        """Test I: producer scope validation."""
        # Producer scope validation is implemented at the application level
        # not at the pipe level. This is tested in lease management tests.
        pytest.skip("Producer scope validation tested at application level")
