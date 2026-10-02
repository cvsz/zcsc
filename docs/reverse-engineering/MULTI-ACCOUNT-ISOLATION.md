# Multi-Account Isolation Design Comparison

## Goal

Run multiple Camfrog accounts online at the same time, with one persistent isolated environment per account. The companion app must never store Camfrog passwords, session tokens, or other login material. Users sign in to Camfrog themselves inside each environment.

Static inspection of the supplied client found references to `Software\Camfrog\Client`, `LOCALAPPDATA`, and `USERPROFILE`. A narrow string scan did not find a recognized per-process portable/profile-directory switch. This is not proof that no such switch exists. The client also has no confirmed custom-status color or marquee fields; see [CSPacket020401-RE.md](CSPacket020401-RE.md).

## Option A: one Windows user profile per account

The stack creates or uses a separate local Windows user for each Camfrog account and starts the Camfrog GUI under that user's identity. Windows profiles contain a per-user registry hive mapped to `HKEY_CURRENT_USER` and per-user folders; Windows documents these settings as unique to each profile. [About User Profiles](https://learn.microsoft.com/en-us/windows/win32/shell/about-user-profiles)

| Dimension | Assessment |
|---|---|
| Isolation | Separate user token, profile folders, and `HKCU`; all processes still share the host Windows kernel and machine-wide state. This is suitable for separating ordinary per-user Camfrog state, but it is not a VM boundary. |
| Resource use | Lowest of the two options: no guest OS is running for each account. |
| Persistence | Native; each account retains its profile between launches. |
| Launch complexity | Medium/high. Starting a process as another user and loading its real registry profile needs the correct token/profile setup. Microsoft documents additional privileges and interactive window-station/desktop ACL work for `CreateProcessAsUser`; `CreateProcessWithLogonW` can load a profile, but requires credentials at launch and has specific profile-loading behavior. [CreateProcessAsUser](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuser), [CreateProcessWithLogonW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw) |
| Visible simultaneous clients | Potentially possible in the current interactive desktop, but this is a Windows integration gate, not something static analysis can guarantee. It must be proven on the target Windows edition with multiple non-focused Camfrog windows. |
| Companion control | A host-side controller could target each process/window by PID and profile SID after launch. The current controller does not carry this profile identity; it now stops when multiple Camfrog client windows are eligible instead of choosing one silently. |
| Operational burden | Create/manage local Windows users, their permissions, first sign-in/profile creation, Camfrog first-run setup, and recovery if a user profile becomes unavailable. Do not put account passwords in the companion config. |

### Stack shape

`Profile manager → Windows-user launcher → Camfrog process → PID/window-bound UI Automation`

Each companion profile stores only a label, Windows user SID, enabled state, and non-secret status/room preferences. Sign-in to Camfrog remains manual. The manager must fail closed if it cannot prove which PID belongs to the selected profile.

## Option B: one persistent Hyper-V VM per account

The stack provisions a persistent VM for each account and runs Camfrog plus a small companion agent inside that VM. Hyper-V is available on Windows Pro/Enterprise editions with hardware virtualization, SLAT, VM-monitor extensions, DEP, and sufficient host memory. Microsoft lists 4 GB as a minimum and requires additional memory for the host and each running VM. [Hyper-V system requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/host-hardware-requirements)

| Dimension | Assessment |
|---|---|
| Isolation | Strongest of these two options: each guest has its own Windows kernel, registry, user profiles, and disk. Use separate guest disks and avoid writable host-folder sharing for account state. |
| Resource use | Highest. Each online account runs a full Windows guest; memory, CPU, storage, and startup cost scale with VM count. |
| Persistence | Strong. Guest disks preserve Camfrog settings and login state between VM starts; protect and back up those disks as sensitive user data. |
| Launch complexity | High. The custom stack must provision/configure VMs, install/update the client and agent, start/stop guests, detect health, and recover from failed startup. Host Hyper-V setup is privileged and edition/hardware dependent. |
| Visible simultaneous clients | Natural at the VM level: each guest has its own desktop. Host-side window scraping is not the same as guest UI Automation; automation should run inside each guest or use a carefully scoped control channel. |
| Companion control | Per-VM companion agent can bind UI Automation to the one local Camfrog process. A host control plane can coordinate named profiles without reading Camfrog credentials. |
| Operational burden | Highest. Keep guest OS updates, Camfrog updates, VM disk backups, network settings, agent versions, and resource allocations consistent. |

### Stack shape

`Host control plane → Hyper-V VM per profile → in-guest companion agent → local Camfrog UI Automation`

The host component stores VM identifiers and non-secret automation preferences only. The guest agent owns local UIA work and reports process/window health. Pairing and control-channel authentication would need a separate design before implementation; do not expose guest control ports broadly.

## Option C: one Windows Server RDS session per account

Run Camfrog in separate Remote Desktop Services user sessions on a Windows Server Session Host. Microsoft's RDS Host supports session-based user desktops and RemoteApp programs; each session gets its own Windows user context while sessions share the server OS. [RDS overview](https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/remote-desktop-services-overview)

| Dimension | Assessment |
|---|---|
| Isolation | Separate logon session, user profile, and `HKCU`, but shared Windows kernel and machine-wide settings. Less isolation than a VM. |
| Resource use | Usually between A and B: each account uses a session and Camfrog process, without a separate guest OS per account. Actual media workload needs measurement. |
| Persistence | User profiles persist across reconnects; a disconnected session can remain available for reconnect according to deployment policy. |
| Launch complexity | Medium/high. Configure RDS roles, accounts, licensing, profile policy, session limits, and per-session startup. |
| Visible simultaneous clients | Separate RDP desktop sessions can run at once. A Camfrog controller must run inside each session and target its local PID/window; a controller in another session cannot be assumed to automate it. |
| Operational burden | Requires Windows Server and compliant RDS licensing. Microsoft says each user or device connecting to a Windows Server RDS Session Host needs an RDS CAL. [RDS CAL requirements](https://learn.microsoft.com/en-us/windows-server/remote/remote-desktop-services/rds-client-access-license) |

### Stack shape

`RDS Session Host → Windows session per profile → Camfrog + per-session companion agent`

This is a useful middle option when separate interactive sessions are needed and shared-kernel isolation is acceptable. It is a multi-session host, not a project-built VM boundary.

## Do not use Windows Sandbox for persistent account sessions

Windows Sandbox is a Microsoft disposable VM, not the persistent multi-VM design above. Microsoft documents that closing it deletes its software/files/state and that only one Windows Sandbox instance can run at a time. Its networking is enabled by default unless disabled in its configuration. Those properties make it a poor fit for several persistent online accounts. [Windows Sandbox overview](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview), [Sandbox configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)

## Windows Sandbox vs Sandboxie-Plus (reference comparison)

This comparison is for choosing requirements; it does not add either product as a dependency to this project.

| Dimension | Windows Sandbox | Sandboxie-Plus |
|---|---|---|
| Isolation model | Disposable hypervisor VM with a separate kernel. | Process-level box that virtualizes file and registry changes; processes still run on the host Windows kernel. |
| Concurrent boxes | Microsoft currently documents one running instance at a time. | Project documentation says multiple independent boxes can run simultaneously. |
| State | Closing the Sandbox deletes installed software and all state. | Box files and registry hive are stored under the sandbox folder and remain until cleared/recovered. |
| Camera / media | Video input is off by default but can be enabled in `.wsb`; microphone input is enabled by default in standard config. | Uses host Windows process/device environment subject to Sandboxie rules; Camfrog device access still needs a real test. |
| Camfrog fit | Poor for persistent, simultaneously online accounts. | Better feature match for one persistent box per account, if Camfrog's own multi-instance behavior allows it. |

Sources: [Windows Sandbox overview/configuration](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview), [Sandboxie-Plus project](https://github.com/sandboxie-plus/Sandboxie), and [Sandboxie registry hive layout](https://sandboxie-plus.com/sandboxie/sandboxhierarchy/).

For this project's own stack, Sandboxie-Plus is a useful behavior reference (multiple persistent boxes with separate file/registry state). Camfrog still needs a Windows proof that separate boxes yield separate client instances and that each helper can bind to the correct box/process. The companion app must not treat box labels alone as proof of process identity.

## Option D: use Sandboxie-Plus as an optional backend

This is the shortest path to the requested Sandboxie-style behavior without writing a new kernel driver and process-hook system. Keep the Sandboxie engine as a separate Windows component and let zcsc own the Camfrog profile UI, configuration, and process-to-profile association.

The linked `Sandboxie/` source subtree is not a one-file library. Its build guide calls the instructions there “Sandboxie Classic”; the repository has a separate `SandboxiePlus/` tree. A build of that subtree produces core components, not automatically the complete Sandboxie-Plus product or installer. The documented core includes the kernel driver (`SbieDrv`), service (`SbieSvc`), and injected DLL (`SbieDll`). Building the x64 release requires Visual Studio 2022, the current Windows SDK, MSVC v143/MFC, and a matching WDK; the guide builds Win32 DLL components first, then the x64 solution and driver. Follow the pinned upstream tag's build/CI instructions rather than copying commands from `master`. [Sandboxie source tree](https://github.com/sandboxie-plus/Sandboxie/tree/master/Sandboxie), [Sandboxie build guide](https://github.com/sandboxie-plus/Sandboxie/blob/master/Sandboxie/ReadMe.md)

### zcsc adapter shape

1. Create one Sandboxie box per `profile_id`, with a unique box name and persistent file root. Do not reuse a box for another account.
2. Launch Camfrog through Sandboxie's `Start.exe` using `/box:<box-name>` and the configured executable path. Use argument arrays with `shell=False`.
3. Query that box's PID list with `Start.exe /box:<box-name> /listpids`; the documented output begins with a count followed by PIDs. Validate the output format against the pinned build before relying on it.
4. For every status or room action, resolve the window PID and verify it belongs to the selected box's live PID set. Refresh associations after process restarts; refuse ambiguous or unboxed windows.
5. Keep Camfrog login interactive in each box. The zcsc profile record stores the box name and non-secret automation settings, never Camfrog passwords or session tokens.

Sandboxie documents `/box:<name>` for launch, `/listpids` for listing processes in a box, and `FileRootPath` for selecting that box's persistent file root. Its installer installs the kernel driver and service, so this is a machine-level dependency with an elevated install/update/uninstall path, not something to fold into the Python one-file EXE. A rebuilt x64 driver also has to satisfy Windows kernel-mode signing policy; a locally built binary is not automatically a production-loadable driver. [Start command line](https://sandboxie-plus.com/sandboxie/startcommandline/), [FileRootPath](https://sandboxie-plus.com/sandboxie/filerootpath/), [Windows kernel-mode signing](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/kernel-mode-code-signing-requirements--windows-vista-and-later-)

`Sandboxie/COPYING` contains the GNU GPL version 3. The zcsc repository's root license is MIT, so do not copy or link Sandboxie source into the app/template without resolving the distribution and source-offer obligations. Keep the engine separately built and packaged as an optional component, preserve its notices, and review the exact combined distribution before shipping; separation reduces code coupling but is not a substitute for license review. [Sandboxie COPYING](https://github.com/sandboxie-plus/Sandboxie/blob/master/Sandboxie/COPYING)

### Fit against the current controller

The existing controller is not profile-aware: `find_processes()` collects every process whose name contains `camfrog`, `ensure_running()` treats any one such process as “Camfrog is running,” and `_find_window_by_pid()` selects the highest-scoring window across all those PIDs. Therefore, adding a Sandboxie launch command alone would still send controls to the wrong account. Refactor to a profile manager plus a controller bound to a box/PID set before enabling multi-account actions. See [controller.py](../../camfrog/controller.py) and [detector.py](../../camfrog/detector.py).

## Sandboxie-inspired profile contract

The required behavior is stronger than opening several Camfrog windows. Every profile must have:

1. A stable, random `profile_id` that is never reused for another account.
2. Persistent file state and registry state owned by that profile. A profile must not read or overwrite another profile's Camfrog state through the normal launch path.
3. An OS-enforced isolation identity (for example, a Windows user SID or AppContainer SID) recorded against the profile.
4. An explicit process association: profile ID, isolation SID, root PID, child PIDs, and any assigned Job Object. Before UI Automation sends an action, resolve `HWND → PID → token SID → profile_id` and refuse the action if any link is missing or ambiguous.
5. Recovery and deletion rules scoped to one profile. Removing a profile must never remove another profile's state.

The profile database stores only non-secret metadata and automation preferences. Camfrog sign-in stays user-driven; do not store Camfrog passwords, cookies, or session tokens. Do not use process titles, executable paths, or a friendly box label as the only identity check.

### Project-owned stack and backend boundary

Build the profile manager, persistent state layout, launcher interface, process-to-profile registry, and per-profile controller as project-owned components. Keep the enforcement backend behind that interface so a future driver-backed implementation does not change profile IDs or controller APIs.

If avoiding the external Sandboxie engine is a higher priority, evaluate AppContainer using Windows' `Experimental_CreateProcessInSandbox` API as an alternative backend. A unique identity selects an AppContainer profile/SID; the specification can grant explicit writable/read-only filesystem paths, capabilities, and network access. Windows documents these APIs as experimental, available on Windows 11, and subject to change. They are a candidate for a project-owned launcher, not a confirmed drop-in Sandboxie replacement. Their path grants describe allowed access; they do not by themselves prove that every Camfrog file and registry write is transparently redirected into a private per-profile overlay. Registry isolation, CEF child-process behavior, camera/microphone access, room UI automation, and simultaneous logins are mandatory Windows compatibility gates. [Create Process in Sandbox APIs](https://learn.microsoft.com/en-us/windows/win32/secauthz/createprocessinsandbox), [AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)

If AppContainer cannot preserve the Camfrog behavior and per-profile registry/file state, use separate Windows user profiles as the lower-complexity fallback: they provide separate user profile directories and `HKCU` hives, but do not provide a Sandboxie-style file/registry overlay or a separate kernel. A true transparent overlay within one Windows user would need a separately designed enforcement backend (such as a signed file-system/registry driver plus carefully scoped process hooks). Treat that as a security-critical Windows product component with install/update/uninstall, signing, crash recovery, and isolation testing—not as a small extension to the Python status helper. Do not implement user-mode-only path or registry rewriting and describe it as a security boundary.

### Process association invariants

- Generate one unique OS isolation identity per profile; never launch two account profiles with the same identity.
- Persist the root PID and verify every controlled Camfrog window's process token identity against the selected profile before applying status, joining a room, or invoking an owner setting.
- Track child processes by verified token identity and Job Object membership where available. If a child escapes the expected identity/job or the identity cannot be queried, mark that process unowned and do not automate it.
- Rebuild process associations after restarts from OS identity and live process handles; do not trust stale PIDs from disk.
- If profile identity and process identity disagree, stop automation and report the mismatch. Never fall back to “first Camfrog window found.”

The current companion controller discovers Camfrog processes globally and selects a window without profile identity. That behavior must be replaced before multi-account launch or automation is enabled.

## Recommendation

For the stated requirement—multiple online accounts at once, persistent file/registry state per profile, and deterministic process ownership—use upstream Sandboxie as the optional isolation backend before building a new driver/hooks stack. First prove the current signed Sandboxie package launches two copies of the exact Camfrog build into separate named boxes, preserves each box's file/registry state, and maps each UI window to the correct box PID list. Then implement the zcsc profile manager and adapter. If the integration must ship a modified Sandboxie engine, pin and build the whole upstream product on Windows, resolve GPL distribution obligations, and complete the driver-signing path before packaging. AppContainer remains an alternative if avoiding Sandboxie is a higher priority, but its Camfrog and registry compatibility is also unverified.

Option B (persistent Hyper-V VM per profile) remains the strongest ready-made OS boundary when custom driver development is out of scope. Option C (RDS) or Option A (separate Windows user profiles) can provide distinct user hives with less resource overhead but share the host kernel. Windows Sandbox remains unsuitable for persistent simultaneous profiles.

For the Windows-user, Sandboxie, AppContainer, or VM backends, do not modify Camfrog internals or call private Camfrog RVAs. Status changes, room joins, and owner tools must use Camfrog's visible controls and its current authorization state. Any future driver/hooks backend is limited to enforcing profile state isolation; it must not become a second path for changing Camfrog status or issuing room commands. Disruptive moderation actions should be individually configurable and require an explicit confirmation before execution.

## Required evidence before choosing a production implementation

- Host Windows edition, hardware virtualization status, memory/storage budget, and number of concurrent accounts.
- A Windows proof that multiple Camfrog logins stay online and their windows can be mapped deterministically to profile IDs.
- A recovery approach for Camfrog updates, profile corruption, VM disk restore, and client reconnect.
- Visible UIA maps for room join and the actual owner settings/actions available to the signed-in account.
- A decision on the initial room-owner actions. The binary contains moderation strings, but strings do not prove command behavior or privilege checks.
