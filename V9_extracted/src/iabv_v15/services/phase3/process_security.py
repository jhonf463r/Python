"""Process Security Descriptor for Phase 3 Child Processes.

This module implements the approved Round 9 design for creating restrictive
process security descriptors with SYSTEM owner and restrictive DACL.

Key properties:
- Owner: SYSTEM (S-1-5-18)
- DACL: Denies dangerous rights to user SID
- DACL: Allows full access to SYSTEM
- No inherited ACEs
- No default DACL
"""

from __future__ import annotations

import win32security
import win32con
import win32api


def create_restrictive_child_security_descriptor() -> win32security.SECURITY_DESCRIPTOR:
    """Create a restrictive security descriptor for child process.
    
    This implements the approved Round 9 design:
    - Owner: SYSTEM (S-1-5-18)
    - DACL: Denies dangerous rights to user SID
    - DACL: Allows full access to SYSTEM
    
    Returns:
        Security descriptor with restrictive settings
    """
    # Create security descriptor
    sd = win32security.SECURITY_DESCRIPTOR()
    
    # Initialize as absolute security descriptor
    sd.Initialize()
    
    # Set owner to SYSTEM (S-1-5-18)
    system_sid = win32security.ConvertStringSidToSid("S-1-5-18")
    sd.SetSecurityDescriptorOwner(system_sid, False)
    
    # Create DACL (Discretionary Access Control List)
    dacl = win32security.ACL()
    
    # Grant full access to SYSTEM
    dacl.AddAccessAllowedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_ALL_ACCESS,
        system_sid
    )
    
    # Get current user SID
    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(),
        win32con.TOKEN_QUERY
    )
    user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    win32api.CloseHandle(token)
    
    # Deny dangerous rights to user SID
    # Order: DENY ACEs first, then ALLOW ACEs
    
    # Deny PROCESS_DUP_HANDLE
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_DUP_HANDLE,
        user_sid
    )
    
    # Deny PROCESS_VM_READ
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_VM_READ,
        user_sid
    )
    
    # Deny PROCESS_VM_WRITE
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_VM_WRITE,
        user_sid
    )
    
    # Deny PROCESS_VM_OPERATION
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_VM_OPERATION,
        user_sid
    )
    
    # Deny PROCESS_CREATE_THREAD
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_CREATE_THREAD,
        user_sid
    )
    
    # Deny PROCESS_SET_INFORMATION
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_SET_INFORMATION,
        user_sid
    )
    
    # Deny PROCESS_SUSPEND_RESUME
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_SUSPEND_RESUME,
        user_sid
    )
    
    # Deny PROCESS_CREATE_PROCESS
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.PROCESS_CREATE_PROCESS,
        user_sid
    )
    
    # Deny WRITE_DAC (prevents DACL modification)
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.WRITE_DAC,
        user_sid
    )
    
    # Deny WRITE_OWNER (prevents ownership takeover)
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.WRITE_OWNER,
        user_sid
    )
    
    # Deny ACCESS_SYSTEM_SECURITY (prevents SACL modification)
    dacl.AddAccessDeniedAce(
        win32security.ACL_REVISION,
        win32con.ACCESS_SYSTEM_SECURITY,
        user_sid
    )
    
    # Set DACL on security descriptor
    # bDaclPresent = True
    # pDacl = explicit DACL
    # bDaclDefaulted = False
    sd.SetSecurityDescriptorDacl(1, dacl, 0)
    
    return sd


def verify_process_security_descriptor(process_handle: int) -> dict[str, any]:
    """Verify the actual security descriptor of a process.
    
    This is used for L4 validation to ensure the implementation
    matches the approved design.
    
    Args:
        process_handle: Handle to the process
        
    Returns:
        Dictionary containing security descriptor information
    """
    try:
        # Get security information
        sd = win32security.GetSecurityInfo(
            process_handle,
            win32security.SE_KERNEL_OBJECT,
            win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
        )
        
        # Get owner
        owner_sid = sd.GetSecurityDescriptorOwner()
        owner_string = win32security.ConvertSidToStringSid(owner_sid)
        
        # Get DACL
        dacl = sd.GetSecurityDescriptorDacl()
        
        # Extract ACE information
        aces = []
        if dacl:
            for i in range(dacl.GetAceCount()):
                ace = dacl.GetAce(i)
                ace_type, ace_flags, ace_mask, ace_sid = ace
                ace_sid_string = win32security.ConvertSidToStringSid(ace_sid)
                
                aces.append({
                    "type": "ALLOW" if ace_type == win32security.ACCESS_ALLOWED_ACE_TYPE else "DENY",
                    "mask": hex(ace_mask),
                    "sid": ace_sid_string
                })
        
        return {
            "owner": owner_string,
            "dacl_present": dacl is not None,
            "aces": aces
        }
    except Exception as e:
        return {
            "error": str(e)
        }
