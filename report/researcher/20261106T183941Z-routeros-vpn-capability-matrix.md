# RouterOS VPN Client Capability Matrix — Vendor-Documented Research Report

- **Agent / role:** researcher sub-agent (vendor documentation research)
- **Objective:** RouterOS **client-side** VPN capability matrix per protocol (WireGuard, SSTP, L2TP/IPsec, OpenVPN), CHR image/licensing facts, and multi-tunnel / management-only routing notes, for RouterOS v6.49.x (latest v6 line) and v7.x — to inform MicroTix's server-side VPN gateway on Debian (tenant MikroTik routers connect OUT as clients).
- **Starting branch / SHA:** `main` @ `7d600146bd643b48f41b71ce5412c8d5abb89e06` (verified with `git rev-parse HEAD`)
- **Date (UTC):** 2026-11-06
- **Permitted write:** this file only. No code, docs, or other repo files were modified; nothing committed or pushed. No credentials/tokens/secrets are included.
- **Relevant project docs:** CONTRACT.md §7 (GNS3 lab, properly licensed CHR, no image redistribution), §8 (network safety), docs/ROUTEROS.md §1–2 (RouterOS v7 for mutation/cutover, v6 read-only; enrollment must not change default routes; private key generated on the router).

## Method & source classes

Sources fetched live during this session (read-only HTTP GET, summarized — no full copyrighted pages reproduced):

1. **Frozen Confluence docs** (`https://help.mikrotik.com/docs/display/ROS/...`, last-updated Apr 2026; site banner states it is frozen and superseded by `https://manual.mikrotik.com`).
2. **Current official manual** (`https://manual.mikrotik.com/docs/...`, Docusaurus, **RouterOS documentation version 7.26**), including the per-menu CLI Reference and versioned pages 7.24/7.25.
3. **MikroTik forum** (`https://forum.mikrotik.com`) — official release-announcement threads and staff replies.
4. **IANA** service-names-port-numbers registry (for conventional port verification).
5. **mikrotik.com/download** (CHR image acquisition page; Livewire-rendered, static links not extractable — CHR widget data loads via AJAX; content cross-cited from the two doc sites instead).

**Access limitations (verified):** `wiki.mikrotik.com` (v6-era wiki) now returns HTTP 307 → `https://help.mikrotik.com/docs/` for `Manual:Interface/*` pages (v6 page bodies no longer served); `web.archive.org` is unreachable from this environment (connection timeout). Therefore some v6-specific statements are grounded in the v7.1 release changelog (which lists features as *new* in v7.1) and in MikroTik staff forum statements, and are explicitly marked INFERENCE where the v6 page itself could not be read.

Citation keys used below: **[WG-HELP]**, **[WG-MAN]**, **[WG-CLI]**, **[WG-PEERS]**, **[7.1-REL]**, **[SSTP-HELP]**, **[SSTP-MAN]**, **[SSTP-CLI]**, **[L2TP-HELP]**, **[L2TP-CLI]**, **[IPSEC-MAN]**, **[IKEV2EAP]**, **[OVPN-HELP]**, **[OVPN-MAN]**, **[OVPN-CLI]**, **[FORUM-OVPN-UDP]**, **[FORUM-SSTP-EAP]**, **[FORUM-2SSTP]**, **[CHR-HELP]**, **[CHR-LIC]**, **[CHR-INST]**, **[DL]**, **[POLICYRT]**, **[V6V7]**, **[IANA]** — URLs listed in **Sources** at the end.

---

## 1. WireGuard client on RouterOS

### Version availability
- **VERIFIED:** WireGuard support was introduced with **RouterOS 7.1** (released 2021-12-01). The official v7.1 release announcement lists under VPN: "!) support for WireGuard" (same changelog block also lists "support for OpenVPN UDP transport protocol", "support for L2TPv3", "support for ZeroTier on ARM/ARM64"). **[7.1-REL]**
- **INFERENCE:** No v6 backport exists — v6.49.x has no WireGuard (the 7.1 changelog presents WireGuard as new; no v6 WireGuard page exists in any reachable MikroTik documentation; no v6 WireGuard release note was found). Treated as fact-by-changelog, not by reading a v6 page.

### Interface (`/interface wireguard`) fields — VERIFIED **[WG-HELP]**, **[WG-CLI]**
- `listen-port` (integer; **Default: 13231**) — "Port for WireGuard service to listen on for incoming sessions." (Note: RouterOS's own default is 13231, *not* 51820.)
- `mtu` (integer 0..65536; **Default: 1420**) — Layer-3 MTU.
- `private-key` (string, **sensitive**; Default: empty) — "**If not specified, it will be automatically generated upon interface creation.**"
- `vrf` (Default: main) — applies to the **UDP socket** carrying encrypted packets, not the WG interface itself; selects the routing table/VRF for encrypted traffic and source IP. **[WG-HELP]**, **[WG-MAN]**
- Read-only: `public-key` (derived), `running`.
- Docs state: "Adding a new WireGuard interface automatically generates a pair of private and public keys. You will need to configure the public key on your remote devices." and "A private key is never needed on the remote side device — hence the name private." **[WG-HELP]**, **[WG-MAN]**

### Key management — VERIFIED
- Keypair is generated **locally on the router** when the interface is created without a private key **[WG-HELP]**, **[WG-MAN]**, **[WG-CLI]** — only the public key is exchanged with the peer (matches docs/ROUTEROS.md §2: "Private key dibuat router, tidak dikirim ke platform").
- `preshared-key` on a peer: "auto generates the key automatically" — optional extra symmetric layer. **[WG-PEERS]**

### Peer fields (`/interface wireguard peers`) — VERIFIED **[WG-HELP]**, **[WG-PEERS]**
- `allowed-address` (**mandatory**; IP/IPv6 prefixes): "List of IP (v4 or v6) addresses with CIDR masks **from which incoming traffic for this peer is allowed and to which outgoing traffic for this peer is directed**. … Allowed-address ranges cannot overlap on one interface, so you need to set own range for each peer." **[WG-HELP]**
- `endpoint-address` (IP/hostname), `endpoint-port` (0..65535) — the UDP port the remote peer listens on.
- `persistent-keepalive` (0..65535; Default 0): "how often to send an authenticated empty packet to the peer for the purpose of keeping a stateful firewall or NAT mapping valid persistently… behind NAT… an interval of 25 seconds" **[WG-HELP]**
- `responder` (yes|no; Default no): "Should be used on WireGuard devices that are used as 'servers'… Otherwise router will all repeatedly try to connect 'endpoint-address'." **[WG-HELP]**
- `name` (peer label for logs) — "Available from RouterOS version 7.15." **[WG-HELP]**
- Read-only: `current-endpoint-address/port`, `last-handshake`, `rx`, `tx`.
- Import/export: `wg-import` (config file; `config-string` parameter added in 7.19_ab41); `wg-export`; `show-client-config` (QR; viewing the QR requires `show-sensitive` from 7.21_ab548; `client-allowed-address` configurable from 7.21). **[WG-HELP]**, **[WG-MAN]**

### MTU caveats — VERIFIED
- Default MTU is **1420** (docs property table). **[WG-HELP]**, **[WG-CLI]** (No further MTU guidance is given on the WireGuard page; deeper MTU/MSS tuning would be lab-verified, not vendor-documented.)

### Ports — VERIFIED / noted
- Docs' own examples use **endpoint port 51820** ("Endpoint = 192.0.2.10:51820") **[WG-MAN]** and also `13231` in setup examples **[WG-HELP]**.
- **51820 is NOT in the IANA service-names-port-numbers registry** (checked the full registry: entries exist for `openvpn 1194`, `l2tp 1701`, `isakmp 500`, `ipsec-nat-t 4500`, `https 443`; no 51820/wireguard entry). **[IANA]** → 51820 is a WireGuard-project convention, not an IANA-registered service port; RouterOS's default listen-port is 13231.

### Multi-WAN / client behavior — VERIFIED **[WG-MAN]**
- "For WireGuard there is no inherent server-client relationship. Both ends can serve as an endpoint and both ends stream UDP handshake messages to each other if they have endpoints defined… You can enable the 'responder' option in the peer settings to emulate server-client behavior."
- Documented Multi-WAN recipe: `responder` on the server side + mangle `add-src-to-address-list` (prerouting, match dst-port=WG listen port, per-WAN in-interface, 1m timeout) + `mark-connection` (output, address-list + src-port) + `mark-routing` (new-routing-mark per WAN) + per-WAN `masquerade` (srcnat, src-port) — "ensures the WireGuard tunnel is established on the interface that received the incoming handshake."

---

## 2. SSTP client on RouterOS

### Existence / versions
- **VERIFIED (partial):** The current documentation states "Starting from v5.0beta2, SSTP does not require certificates to operate and can use any available authentication type" **[SSTP-HELP]**, **[SSTP-MAN]** — which implies SSTP pre-dates v5. **INFERENCE:** SSTP client/server has existed since the RouterOS v4 era; the exact introduction version could not be verified from any reachable official source (v6 wiki unreachable).
- Both v6.49.x and v7.x have `/interface sstp-client` (v6-only inline notes like "Since v6.2" exist for analogous L2TP fields; the SSTP page itself carries v5/v7-era notes). Full v6 field parity could not be re-verified against a v6 page — see Gaps.

### `/interface sstp-client` fields — VERIFIED **[SSTP-HELP]**, **[SSTP-CLI]** (7.26)
- `connect-to` (IP/IPv6, **mandatory**) — remote SSTP server; `port` (**Default: 443**).
- `user` (**mandatory**), `password` (sensitive), `profile` (PPP profile).
- `authentication` (chap | mschap1 | mschap2 | pap; **Default: all**) — **EAP is NOT an option** on the SSTP client. **[SSTP-HELP]**, **[SSTP-CLI]**
- `certificate` (client cert or none); `verify-server-certificate` (yes|no; Default no) — "SSTP client will verify server certificate"; `verify-server-address-from-certificate` (yes|no; Default no) — "SSTP client will verify server address in certificate."
- `tls-version` (**any | only-1.2**; Default any) — "Specifies which TLS version to allow." (No TLS 1.3 option is documented for SSTP.)
- `ciphers` (**aes256-gcm-sha384 | aes256-sha**; Default: all) — allowed cipher suites.
- `pfs` (no | yes | required; Default no) — yes ⇒ ECDHE-RSA/DHE-RSA; required ⇒ ECDHE only.
- `add-default-route` (Default no), `default-route-distance`, `dial-on-demand` (adds a placeholder route from 10.112.112.0/24 while not connected), `keepalive-timeout` (Default 60), `mrru` (Default disabled), `max-mtu`/`max-mru` (**Default 1460**), `http-proxy`/`proxy-port`, `add-sni` (**added 7.15beta10** — adds the TLS SNI extension to client hello if enabled). **[SSTP-HELP]**, **[SSTP-MAN]**

### `verify-method` / `disabled-verify-method` — **NOT FOUND (could not verify)**
- These parameter names do **not** appear in: the frozen help SSTP page (last updated 2026-04-13) **[SSTP-HELP]**; the current manual SSTP page **[SSTP-MAN]**; the RouterOS 7.26 CLI Reference for `/interface sstp-client` **[SSTP-CLI]**; the versioned 7.24 and 7.25 CLI references (fetched and grepped); the L2TP/OVPN client CLI references; MikroTik forum search (`"verify-method"`, `"disabled-verify-method"` — zero posts); nor in the 108 daily documentation-changelog entries at manual.mikrotik.com/changelog (2026-05→2026-11, all fetched and grepped).
- **INFERENCE:** the task premise likely refers to parameters that are either (a) from a non-MikroTik SSTP client implementation, (b) an undocumented/renamed beta property, or (c) a misremembered name. The **documented** SSTP client TLS/certificate validation controls are: `verify-server-certificate`, `verify-server-address-from-certificate`, `certificate`, `tls-version`, `ciphers`, `pfs`. **Recommended next action:** verify on a live lab router (`/interface/sstp-client print` / `set ?`) before relying on any such field.

### Auth: eap vs mschap2/pap — VERIFIED + corroborated
- Docs list only pap/chap/mschap1/mschap2 for the client **[SSTP-HELP]**, **[SSTP-CLI]**. Forum threads document that Windows RRAS/NPS rejects the RouterOS SSTP client's MS-CHAPv2 when EAP is required, with no RouterOS-side EAP option ("router SSTP VPN Client lacks EAP support?", open 2020→2025) **[FORUM-SSTP-EAP]**. So a MicroTix SSTP endpoint **must accept non-EAP PPP auth (e.g., MSCHAPv2)**.

### Transport / certificates — VERIFIED **[SSTP-HELP]**
- "The use of TLS over TCP port 443 allows SSTP to pass through virtually all firewalls and proxy servers"; connection flow: TCP (443) → SSL validates server certificate → SSTP control packets → PPP negotiation/auth.
- Secure mode: server cert + mschap auth, certs from same chain; importing the CA and enabling `verify-server-certificate` on the client prevents MITM. Cert-less mode ("anonymous DH… Man-in-the-Middle attacks are easily accomplished") works **only MikroTik-to-MikroTik** (not per Microsoft standard). RSA keys ≥ 472 bits required.
- v7 client additions: `add-sni` (7.15beta10+) **[SSTP-HELP]**; "ppp - added support for IPv6-only domain names to l2tp-client, ovpn-client and sstp-client" (7.16.2/7.16rc changelog posted on the forum) **[7.1-REL-family: forum topics 178911/177857]**.

---

## 3. L2TP/IPsec client on RouterOS

### `/interface l2tp-client` fields — VERIFIED **[L2TP-HELP]**, **[L2TP-CLI]** (7.26)
- `connect-to` (**mandatory**; IP/IPv6; VRF syntax `192.168.88.1@vrf1`), `user` (**mandatory**), `password`, `profile` (Default `default-encryption`).
- `allow` (mschap2 | mschap1 | chap | pap; Default all) — again **no EAP** on the PPP layer.
- `use-ipsec` (yes|no; Default no): "dynamic IPSec peer configuration and policy (**transport mode**) is added to encapsulate L2TP connection into an IPSec tunnel. **Multiple L2tp/ipsec clients behind the same NAT will not work in this mode.** To achieve such a scenario, disable use-ipsec and set static policies for clients with enabled tunnel=yes, level=unique settings." **[L2TP-HELP]**, **[L2TP-CLI]**
- `ipsec-secret` (sensitive PSK, used when `use-ipsec`).
- `add-default-route` (Default no), `default-route-distance` ("Since v6.2"), `dial-on-demand` (placeholder route from 10.112.112.0/24), `keepalive-timeout` (Default 60; "Since v6.0rc13"), `max-mtu`/`max-mru` (**Default 1450**), `mrru`, `src-address`, `use-peer-dns`, `allow-fast-path` ("Must be disabled if IPsec is used" **[L2TP-CLI]**), `random-source-port`.
- v7-only: `l2tp-proto-version` (l2tpv2 | l2tpv3-ip | l2tpv3-udp) + L2TPv3 cookie/circuit-id/digest fields — "L2TPv3 support added in 7.1 version." **[L2TP-HELP]**

### IPsec side of the L2TP client — VERIFIED **[IPSEC-MAN]**
- "For RouterOS to work as an L2TP/IPsec client, it is as simple as adding a new L2TP client… `/interface/l2tp-client add connect-to=1.1.1.1 disabled=no ipsec-secret=mySecret name=l2tp-out1 password=123 use-ipsec=yes user=user1` — **This automatically creates dynamic IPsec peer and policy configurations.**"
- The documented dynamic peer created for L2TP/IPsec shows: `address=0.0.0.0/0 passive=yes port=500 auth-method=pre-shared-key generate-policy=port-strict exchange-mode=main-l2tp send-initial-contact=yes nat-traversal=yes hash-algorithm=sha1 enc-algorithm=3des,aes-128,aes-192,aes-256 dh-group=modp1024 lifetime=1d dpd-interval=2m dpd-maximum-failures=5` — i.e., the auto mode is **IKEv1-style `main-l2tp` exchange with PSK and NAT-T enabled**, defaults sha1/3des-aes/modp1024. **[IPSEC-MAN]** (v6.49.x behavior believed identical — **INFERENCE**, v6 wiki page unreachable.)
- **IKEv2 client support:** RouterOS can be an IKEv2 *client* with EAP — "Starting from RouterOS v6.45, it is possible to establish an IKEv2 secured tunnel to NordVPN servers using EAP authentication": `/ip/ipsec/peer add address=… exchange-mode=ike2`, `/ip/ipsec/identity add auth-method=eap eap-methods=eap-mschapv2 generate-policy=port-strict mode-config=… responder=no`. **[IKEV2EAP]** — but this is a standalone IPsec client configuration, **not** an option of `/interface l2tp-client` (using IKEv2 *for* L2TP encapsulation via the l2tp-client menu is not documented — see Gaps).

### Ports — VERIFIED
- "L2TP traffic uses UDP… **UDP port 1701 is used only for link establishment**, further traffic is using any available UDP port." **[L2TP-HELP]**; IANA: `l2tp 1701/tcp+udp`, `isakmp 500/tcp+udp`, `ipsec-nat-t 4500/tcp+udp` (RFC 3948/7296). **[IANA]**
- IPsec page: peers "should be reachable through UDP/500 and UDP/4500 ports"; mangle/NAT examples mark/exclude `dst-port=500,4500` and `src-port=500,4500`. **[IPSEC-MAN]**

### NAT traversal — VERIFIED
- Dynamic L2TP/IPsec peer runs with `nat-traversal=yes` **[IPSEC-MAN]**; the NAT caveat for multiple clients behind one NAT is quoted above **[L2TP-HELP]**. For a tenant-side (client) router behind CGNAT this is a design-critical constraint; a single client behind NAT is the normal NAT-T case (RFC 3948 port 4500) **[IANA]**.

---

## 4. OpenVPN client on RouterOS

### TCP vs UDP — VERIFIED with staff sources
- **v6 (6.49.x): TCP-only client.** MikroTik staff (normis) in the v6.36 release thread answering "when will OVPN UDP be implemented?": "**RouterOS 7**, as it was promised in the other topics about this." **[FORUM-OVPN-UDP]** The official v7.1 changelog lists "!) support for OpenVPN UDP transport protocol" as new in 7.1 **[7.1-REL]**. (The exact v6 wiki wording is unreachable — conclusion grounded in the staff statement + 7.1 changelog; marked INFERENCE in Gaps only for the missing v6 page text.)
- **v7: `protocol (tcp | udp; Default: tcp)`** on `/interface ovpn-client` **[OVPN-HELP]**, **[OVPN-CLI]**; `disconnect-notify` ("Sends explicit disconnect notification in UDP mode") present in the 7.26 CLI reference **[OVPN-CLI]**.

### `/interface ovpn-client` fields — VERIFIED **[OVPN-HELP]**, **[OVPN-CLI]**
- `connect-to` (**mandatory**), `port` (**Default: 1194**), `user` (**mandatory**), `password` (sensitive; ≤1000 chars), `profile`, `mode` (ip | ethernet; Default ip), `protocol` (tcp | udp; Default tcp), `max-mtu` (Default 1500).
- `cipher` (null | aes128-cbc | aes128-gcm | aes192-cbc | aes192-gcm | aes256-cbc | aes256-gcm | blowfish128; **Default: blowfish128**): "In order to use GCM type ciphers, the 'auth' parameter must be set to 'null', because GCM cipher is also responsible for 'auth'." ("7.17beta5 added support to allow non-null auth in gcm mode." **[OVPN-HELP]**; the 7.26 manual states non-null auth in GCM mode is supported. **[OVPN-MAN]**)
- `auth` (md5 | sha1 | null | sha256 | sha512 (+ sha384 in 7.26 CLI ref); **Default: sha1**).
- `tls-version` (**any | only-1.2**; Default any) — no TLS 1.3 option documented for the OVPN client.
- `verify-server-certificate` (yes|no; Default no): "Checks the certificates CN or SAN against the 'connect-to' parameter. The IP or hostname must be present in the server's certificate." **[OVPN-HELP]** (7.26 CLI ref adds trust-chain validation against the router's certificate store. **[OVPN-CLI]**)
- `add-default-route`, `use-peer-dns`, `route-nopull` ("Specifies whether to allow the OVPN server to add routes to the OVPN client instance routing table"), `certificate`, `mac-address`.
- Import: `/interface ovpn-client import-ovpn-configuration …`; tls-auth can only be configured via imported .ovpn file. **[OVPN-HELP]**

### Documented client-side constraints that bind the SERVER profile — VERIFIED **[OVPN-HELP]**, **[OVPN-MAN]**
- "**ROS client requires user name and password.** Authentication is managed by server side, if its supports tls, then user name will be ignored."
- "OpenVPN username is limited to **27 characters** and the password to 233 characters. Password cap increased in 7.18_ab253 to 1000 characters." → server-side usernames must be ≤27 chars.
- "NCP autonegotiation" is unsupported → "cipher has to be specified in .ovpn file when connecting to an ROS ovpn server" — i.e., for ROS-to-anything, the data cipher must be explicitly pinned on both ends; our Debian server must offer the exact cipher the client configures.
- LZO compression unsupported (VORACLE risk noted).
- tls-crypt / tls-crypt v2 supported from **7.17rc3**, only with `auth SHA256`, and "no key-direction in the server configuration" / "key-direction 1 in the client configuration". **[OVPN-HELP]**
- TLS-version choices on the client are only `any` or `only-1.2` → the server must tolerate TLS ≤1.2-compatible handshakes for RouterOS clients (no TLS1.3-only server setting is compatible with the documented client options).
- Default cipher `blowfish128` (CBC) and default auth `sha1` — for a modern server profile, MicroTix must explicitly provision `cipher=aes256-gcm`+`auth=null` (or AES-CBC + sha256/sha512) on the client and matching server settings.

---

## 5. CHR — authorized images, licensing tiers, GNS3-lab constraints

### Where to obtain images — VERIFIED
- "Download the CHR Image: Go to the MikroTik download page **Cloud Hosted Router section**; Select the image format for your platform; Download the file." Formats: **RAW `.img`, VirtualBox `.vdi`, VMware `.vmdk`, Hyper-V `.vhdx`, OVA `.ova`** ("disk images only and must be attached to a virtual machine"). **[CHR-INST]**, **[CHR-HELP]** (older page: img/vmdk/vhdx/vdi), **[DL]** (download page at https://mikrotik.com/download — CHR section confirmed present; direct file links are rendered client-side).
- Requirements: "Package version: RouterOS v6.34 or newer"; host CPU 64-bit with virtualization; RAM ≥256 MB (new manual v7 formula `RAM = 512 + 8×CPU×(IF_COUNT−1)`, recommend ≥1024 MiB; older help page used 256 in the formula — doc-version discrepancy noted); disk ≥128 MB; v6 max virtual disk 16 GB. Supported platforms: VMware ESXi/Fusion, Proxmox VE (KVM/QEMU), Hyper-V (Generation 1 only), VirtualBox, Xen Server; **paravirtualization not supported; bhyve not supported**; Fast Path on v7 with vmxnet3/virtio-net. **[CHR-INST]**, **[CHR-HELP]**

### Licensing tiers — VERIFIED **[CHR-LIC]**, **[CHR-HELP]**
| Level | Speed limit (per interface, upload) | Price | Notes |
|---|---|---|---|
| Free | **1 Mbit** | FREE | runs indefinitely, all features |
| P1 (Perpetual-1) | 1 Gbit | $45 | upgradeable to P10/PU |
| P10 (Perpetual-10) | 10 Gbit | $95 | upgradeable to PU |
| P-Unlimited | Unlimited | $250 | highest tier |
| 60-day Trial | any paid tier | FREE | requires MikroTik.com account |

- Licenses are **perpetual**, tied to the CHR **System ID**, managed via the MikroTik account; a running CHR periodically contacts `licence.mikrotik.com` (`next-renewal-at` / `deadline-at`, hourly retries); failure to renew ⇒ behaves as expired trial (no RouterOS upgrades, no package changes, but keeps running). **[CHR-LIC]**
- "You can clone or copy a running CHR system, but cloned instances retain the original trial status" — trials cannot be extended by cloning; `/system/license/generate-new-id` (only valid on Free level) avoids duplicate System IDs when deploying from one image. **[CHR-LIC]**
- IP/Cloud functionality requires a paid perpetual CHR license. **[CHR-LIC]**

### GNS3-relevant constraints
- **VERIFIED:** KVM/QEMU is a supported virtualization platform (Proxmox VE guide; old page: "Qemu 2.4.0.1 on Linux and OS X" tested; virtio/E1000/vmxnet3 NICs on QEMU/KVM). **[CHR-INST]**, **[CHR-HELP]**
- **INFERENCE:** MikroTik documentation does not mention GNS3 by name (checked the CHR installation index — platform guides cover ESXi, Hyper-V, Proxmox, VirtualBox, AWS, Hetzner, Vultr only). Since GNS3 runs routers as QEMU/KVM VMs, CHR is usable there using the official `.img`/converted disk image; this is inference from the QEMU/KVM support statement, to be confirmed in the lab.
- **Contract alignment:** images are distributed only via MikroTik's download page and licensed per System ID (above) — consistent with CONTRACT.md §7 "Use properly licensed CHR images from authorized sources; never redistribute images without rights". The Free tier's 1 Mbit/interface upload limit is the practical constraint for lab throughput benchmarks; 60-day trials require a MikroTik account and expire (plan license strategy for long-lived lab nodes).

---

## 6. Multiple concurrent VPN client tunnels & management-only tunnel notes (only what sources state)

- **Two SSTP clients on one router** (staff reply, tangent): to run two SSTP clients to the same/second server via different ISPs — "The superior option is to give the remote server a second public IP… and then set routing toward the separate ISPs: `/ip/route add dst-address=111.111.111.1 gateway=ether1`, `add dst-address=111.111.111.2 gateway=ether2`." **[FORUM-2SSTP]** (Verifies: multiple concurrent PPP client tunnels are supported, and `/ip route` with an **interface as gateway** steers each tunnel's control traffic.)
- **Interface-as-gateway routes** are the documented pattern for tunnel traffic: `/ip route add dst-address=10.1.101.0/24 gateway=wireguard1` **[WG-HELP]**/**[WG-MAN]**; `add dst-address=10.5.8.20 gateway=ovpn-client1` **[OVPN-HELP]** — i.e., a management-only tunnel can install only the narrow routes it needs (e.g., a /32 to the management server) via `gateway=<tunnel-interface>`, rather than `add-default-route`.
- **v7 routing tables / routing-mark:** "The main difference from v6 is that the routing table must be added to the `/routing/table` menu before actually referencing it… `fib` parameter should be specified if the routing table is intended to push routes to the FIB." Routing rules moved from `/ip route rule` to `/routing/rule`. "Instead of routing rules, you could use mangle to mark packets with routing-mark, the same way as it was in ROSv6." **[V6V7]**
- **Mangle-vs-local caveat (management reachability):** "When you are using mangle to set routing-marks, be careful not to mark 'local' traffic… the router's ip addresses will not be reachable because, by default, mangle is the first in the list and overrides local lookup." Fix: `!dst-address-type=local` in the mangle rule or reorder `/routing/rule`. **[V6V7]**
- **Routing rules / tables:** custom tables via `/routing/table add name=myTable fib`; `/routing/rule add dst-address=… action=lookup-only-in-table table=myTable [interface=…]`; routing-rule count limited to **4096 tables**; rules can also act as a basic firewall (`action=drop`). **[POLICYRT]**
- **IPsec control-plane marking (multi-WAN):** "You must mark UDP/500, UDP/4500, and ipsec-esp packets with Mangle… mark-connection (output, dst-port=500,4500) … mark-routing new-routing-mark=backup" and exclude IPsec from masquerade: `/ip/firewall/nat add action=accept chain=srcnat protocol=udp src-port=500,4500 place-before=0`. **[IPSEC-MAN]**
- **WireGuard reply-path pinning:** the documented Multi-WAN recipe (address-lists + connection marks + routing marks + per-WAN masquerade, with `responder=yes` on the "server" peer) ensures replies leave via the WAN interface that received the handshake. **[WG-MAN]**
- **Firewall filter semantics for management traffic:** "The default RouterOS firewall blocks the [WireGuard] tunnel from establishing properly. The traffic must be accepted in the 'input' chain **before any drop rules**" (accept `dst-port=<wg-port> protocol=udp`). To let tunnel peers reach RouterOS services: allow the WG subnet in input, e.g. `add chain=input action=accept in-interface=wireguard1 src-address=192.168.100.0/24` — and "Alternatively, add the WireGuard interface to the LAN interface list… use separate firewall rules when VPN peers should have less access." **[WG-HELP]**, **[WG-MAN]** (This is the documented basis for a *management-scoped* input policy on the tunnel interface.)
- **NAT caveat for L2TP/IPsec clients:** "Multiple L2tp/ipsec clients behind the same NAT will not work in this mode [use-ipsec]" — relevant if several tenant routers share one public IP. **[L2TP-HELP]**, **[L2TP-CLI]**
- **`persistent-keepalive=25`** keeps NAT mappings alive for rarely-transmitting peers. **[WG-HELP]**

---

## Summary matrix (RouterOS CLIENT side)

| Protocol | v6.49.x client | v7.x client | Conventional port(s) | Key client-side constraints (documented) |
|---|---|---|---|---|
| **WireGuard** | **Not available** *(inference from 7.1 changelog)* | ✅ since **7.1** (2021-12-01); peer `name` 7.15+, `wg-import config-string` 7.19+, `client-allowed-address` 7.21+ | UDP, any; docs default listen-port 13231; examples use 51820 (not IANA-registered) | Keypair auto-generated on router (private key stays local); allowed-address non-overlap per interface; default MTU 1420; keepalive for NAT; `responder` for server role |
| **SSTP** | ✅ (v4/v5-era feature; v6 field set believed near-identical — partly unverifiable) | ✅ (add-sni since 7.15beta10; IPv6-only domain support 7.16.2) | **TCP 443** (client `port` default 443; configurable) | Auth pap/chap/mschap1/mschap2 only (**no EAP**); TLS `any\|only-1.2`; ciphers limited to aes256-sha / aes256-gcm-sha384; `verify-server-certificate` + CA import for MITM protection; `verify-method`/`disabled-verify-method` **not found in any official doc** |
| **L2TP/IPsec** | ✅ (PPP + `use-ipsec`+`ipsec-secret`) | ✅ (plus L2TPv3 since 7.1; `random-source-port`) | UDP **1701** (establishment only) + IPsec **500/4500** (NAT-T) | Auto IPsec = IKEv1-style `main-l2tp`, PSK, transport mode, nat-traversal=yes, defaults sha1/3des-aes/modp1024; multiple clients behind one NAT broken with `use-ipsec`; IKEv2 client exists as standalone `/ip ipsec` config (EAP since v6.45), not via l2tp-client |
| **OpenVPN** | ✅ **TCP-only** (staff: UDP "RouterOS 7") | ✅ TCP+**UDP since 7.1**; tls-crypt 7.17rc3+; non-null auth w/ GCM 7.17beta5+; password cap 1000 chars 7.18+ | **TCP/UDP 1194** default (client `port` configurable) | Username **≤27 chars** & password required; **no NCP** — cipher must be pinned (default blowfish128/sha1); GCM needs auth=null (pre-7.17); tls-version only `any\|only-1.2`; LZO unsupported; verify-server-certificate checks CN/SAN vs connect-to |
| **CHR (lab host)** | v6.34+ package; max 16 GB vdisk; no Fast Path | Full features; Fast Path vmxnet3/virtio-net | n/a | Free tier 1 Mbit/interface upload; P1 $45/1G, P10 $95/10G, PU $250 unlimited; 60-day trial w/ account; images only from mikrotik.com download (img/vdi/vmdk/vhdx/ova); QEMU/KVM supported (GNS3 = inference); license tied to System ID, renewal via licence.mikrotik.com |

---

## Gaps / Inferences (explicit separation)

**Verified facts** are every statement above carrying a citation key. The following could **not** be verified from a reachable official source and are marked as such:

1. **`verify-method` / `disabled-verify-method` (SSTP):** NOT FOUND in the frozen help page, manual 7.24/7.25/7.26 SSTP client CLI reference, L2TP/OVPN client references, MikroTik forum, or the daily documentation changelog. **INFERENCE:** premise may reference another vendor's client or an undocumented/renamed beta property. Action: probe a live RouterOS build in the GNS3 lab (`/interface/sstp-client set ?`).
2. **v6 OpenVPN client "TCP-only":** grounded in (a) MikroTik staff statement in the v6.36 thread (UDP → "RouterOS 7") **[FORUM-OVPN-UDP]** and (b) v7.1 changelog listing OVPN UDP as new **[7.1-REL]**. The v6 wiki page text itself was unreachable (307 redirect). Confidence high; strictly an inference from release notes.
3. **v6 WireGuard absence:** same grounding (7.1 changelog lists WireGuard as new). No v6 release note found adding WireGuard to 6.49.x.
4. **SSTP introduction version:** only "Starting from v5.0beta2…" is documented; v4-era introduction is **INFERENCE**.
5. **v6 field-level parity for SSTP/L2TP/OVPN clients:** could not re-read v6 wiki pages (redirect + archive.org unreachable). Inline version notes in current docs ("Since v6.2", "Since v6.0rc13") are the only v6-anchored, sourced data points.
6. **L2TP-client auto-IPsec customizability:** whether the dynamic peer created by `use-ipsec` can be bound to a custom `/ip ipsec profile` (stronger algorithms than sha1/3des/modp1024) is **not documented**. **INFERENCE:** it appears to use default profile values; must be lab-verified before committing MicroTix server-side IPsec proposals. Using IKEv2 *for L2TP* via the client menu is likewise undocumented.
7. **CHR on GNS3:** supported-virtualization list does not name GNS3; QEMU/KVM support is the sourced basis for GNS3 compatibility (inference).
8. **CHR RAM formula discrepancy:** frozen help page says v7 `RAM = 256 + 8×CPU×(IF−1)`; current manual (7.26) says `RAM = 512 + …`. Both cited; treat the current manual as authoritative and re-check at lab build time.
9. **IANA 51820:** not registered (checked full registry) — "conventional WireGuard port" status comes from WireGuard-project usage, reflected in RouterOS doc examples only.
10. **Download-page file links:** mikrotik.com/download renders CHR file links client-side (Livewire); the "Cloud Hosted Router section" instruction is cited from the manual instead. Image filenames/formats cited from the two doc sites.

---

## Implications for a shared-port multi-protocol gateway design (grounded only in the sourced facts above)

1. **Port steering:** every documented client can target an arbitrary server port — SSTP `port` (default 443), OVPN `port` (default 1194), WG `endpoint-port` (server-defined), L2TP+IPsec is the exception (IKE fixed to UDP 500/4500, L2TP establishment on 1701). A Debian gateway can therefore host WG + OVPN + SSTP on distinct or shared ports per protocol, but L2TP/IPsec reserves 500/4500 (and its own policy) exclusively.
2. **SSTP on 443 with SNI steering:** SSTP's documented selling point is "TLS over TCP port 443 allows SSTP to pass through virtually all firewalls and proxy servers" and v7.15+ clients can add **SNI** to the ClientHello (`add-sni=yes`). This makes TLS/SNI-based front-door routing (e.g., sharing 443 with other TLS services) possible **only for v7.15+ clients** — v6 clients cannot be SNI-routed (documented absence of the option before 7.15beta10).
3. **OpenVPN multiplexing:** "Multiple VPN sessions can be multiplexed over a single TCP or UDP port" **[OVPN-MAN]** — one OVPN port serves all tenants; but the server profile must pin the data cipher/auth (no NCP on RouterOS clients) and keep usernames ≤27 chars; TLS limited to `any|only-1.2` on the client side constrains the server's TLS policy.
4. **SSTP crypto profile:** only two cipher suites are client-selectable (`aes256-sha`, `aes256-gcm-sha384`) with `tls-version any|only-1.2` and PPP auth without EAP — the Debian SSTP endpoint (e.g., accel-ppp-style) must offer exactly one of these suites and MSCHAPv2/PAP-class PPP auth.
5. **L2TP/IPsec server profile:** to accept the router's auto (`use-ipsec`) mode, the server must terminate IKEv1 `main-l2tp` with PSK and accept the default proposal set (sha1; 3des/aes-128/192/256; modp1024) — or MicroTix must move tenants to the documented standalone IKEv2-client pattern (EAP, since v6.45) at the cost of a second configuration path. Multiple tenants behind one NAT cannot all use auto `use-ipsec` against us (documented) — plan static `tunnel=yes level=unique` policies or prefer other protocols for such sites.
6. **WireGuard is the best CGNAT fit:** client-initiated UDP with `persistent-keepalive=25` (NAT keepalive documented), single UDP server port, router-local key generation (private key never leaves the router — aligns with docs/ROUTEROS.md enrollment requirement), `responder=yes` on the server peer emulating server-client behavior.
7. **Management-only scoping:** all tunnel types support interface-gateway routes (`gateway=wireguard1`, `gateway=ovpn-client1`, `gateway=ether1` in the staff SSTP answer) so MicroTix can install only narrow /32 routes to the management host and **must not** use `add-default-route` (also the docs/ROUTEROS.md §1 rule). Input-chain rules matching `in-interface=<tunnel>` + `src-address=<mgmt-subnet>` placed before drop rules are the documented way to scope management access; adding the tunnel to the LAN interface-list is explicitly called out as *broader* access.
8. **Multi-tunnel / multi-WAN safety:** documented patterns exist for running several concurrent client tunnels with per-tunnel routing (routing tables/rules in v7, `routing-mark` mangle as in v6), with the explicit warning that output-mangle marks can break local (router-address) reachability unless local traffic is excluded — directly relevant to keeping the management plane reachable while steering VPN traffic.

---

## Sources (all fetched 2026-11-06; URLs as cited)

- **[WG-HELP]** https://help.mikrotik.com/docs/display/ROS/WireGuard (frozen Confluence, updated 2026-04-15)
- **[WG-MAN]** https://manual.mikrotik.com/docs/virtual-private-networks/wireguard (RouterOS Manual 7.26)
- **[WG-CLI]** https://manual.mikrotik.com/docs/cli-reference/interface/wireguard/
- **[WG-PEERS]** https://manual.mikrotik.com/docs/cli-reference/interface/wireguard/peers/
- **[7.1-REL]** https://forum.mikrotik.com/t/153754 ("v7.1 is released!", MikroTik staff changelog, 2021-12-01; also forum topics 178911 & 177857 for the 7.16.2/7.16rc "IPv6-only domain names" PPP entry)
- **[SSTP-HELP]** https://help.mikrotik.com/docs/display/ROS/SSTP (frozen Confluence, updated 2026-04-13)
- **[SSTP-MAN]** https://manual.mikrotik.com/docs/virtual-private-networks/sstp
- **[SSTP-CLI]** https://manual.mikrotik.com/docs/cli-reference/interface/sstp-client/ (also checked versioned 7.24/7.25)
- **[FORUM-SSTP-EAP]** https://forum.mikrotik.com/t/142993 ("router SSTP VPN Client lacks EAP support?")
- **[FORUM-2SSTP]** https://forum.mikrotik.com/t/168859 ("2 SSTP clients to same remote IP, each VPN through different ISP" — staff reply by tangent)
- **[L2TP-HELP]** https://help.mikrotik.com/docs/display/ROS/L2TP (frozen Confluence, updated 2026-04-15)
- **[L2TP-CLI]** https://manual.mikrotik.com/docs/cli-reference/interface/l2tp-client/
- **[IPSEC-MAN]** https://manual.mikrotik.com/docs/virtual-private-networks/ipsec/ (incl. "Basic L2TP/IPsec setup", Multi-WAN IPsec mangle/NAT examples)
- **[IKEV2EAP]** https://manual.mikrotik.com/docs/virtual-private-networks/ipsec/ikev2-eap-between-nordvpn-and-routeros
- **[OVPN-HELP]** https://help.mikrotik.com/docs/display/ROS/OpenVPN (frozen Confluence, updated 2026-04-15)
- **[OVPN-MAN]** https://manual.mikrotik.com/docs/virtual-private-networks/openvpn
- **[OVPN-CLI]** https://manual.mikrotik.com/docs/cli-reference/interface/ovpn-client/
- **[FORUM-OVPN-UDP]** https://forum.mikrotik.com/t/100032 (v6.36 release thread — staff reply: OVPN UDP in "RouterOS 7"); corroborating threads: https://forum.mikrotik.com/t/23563 , https://forum.mikrotik.com/t/147694 , https://forum.mikrotik.com/t/175789
- **[CHR-HELP]** https://help.mikrotik.com/docs/display/ROS/Cloud+Hosted+Router,+CHR (frozen Confluence, updated 2026-04-17)
- **[CHR-LIC]** https://manual.mikrotik.com/docs/getting-started/routeros-licensing/chr/chr-licensing
- **[CHR-INST]** https://manual.mikrotik.com/docs/getting-started/installation-and-upgrade/install/chr-installation/
- **[DL]** https://mikrotik.com/download (Cloud Hosted Router section)
- **[POLICYRT]** https://manual.mikrotik.com/docs/user-guides/routing-and-networking-protocols/policy-routing
- **[V6V7]** https://manual.mikrotik.com/docs/user-guides/routing-and-networking-protocols/moving-from-rosv6-to-rosv7
- **[IANA]** https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.txt

## Completion state & next steps

- **Completion state:** research complete for all six task areas; one report file written (this file); no other repo changes. NOT PUSHED (no commits made, per instructions).
- **Next executable steps for the orchestrator:**
  1. Lab-verify the SSTP `verify-method`/`disabled-verify-method` premise on a live CHR (`/interface/sstp-client set ?` / WinBox) — currently unsupported by any reachable official doc.
  2. Lab-verify whether L2TP-client auto-IPsec honors a custom `/ip ipsec profile` (stronger than sha1/3des/modp1024) before freezing MicroTix's strongSwan proposal set.
  3. Decide server profiles per protocol from §Implications (SSTP suite+MSCHAPv2; OVPN pinned cipher + ≤27-char usernames + TLS≤1.2 tolerance; WG on a dedicated UDP port; L2TP/IPsec IKEv1 main-l2tp PSK defaults or the IKEv2/EAP alternative).
  4. Obtain CHR images for the GNS3 lab exclusively from mikrotik.com/download (no redistribution) and plan licensing (Free vs 60-day trial vs P1) per §5.
