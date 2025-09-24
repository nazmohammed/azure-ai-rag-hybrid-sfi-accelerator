# DevTunnel 
## 1. Install DevTunnel

Run Powershell --> 
winget install Microsoft.devtunnel 

Found devtunnel [Microsoft.devtunnel] Version 1.0.1435.39636 successfully installed

## 2. Sign into you Azure Account

devtunnel user login  [This opens a browser to authenticate with your Microsoft/Azure identity.]

## 3. Create a new tunnel


## devtunnel create myragbot --port 3978 --allow-anonymous
<img width="850" height="153" alt="image" src="https://github.com/user-attachments/assets/6bdc5d0b-d58a-4086-96b6-dbdb8ec59a75" />


## Description:
  Host a tunnel, if tunnel ID is not specified a new tunnel will be created

Usage:
  devtunnel host [<tunnel-id>] [options]

Arguments:
  <tunnel-id>  Existing tunnel ID (optional)

Options:
  -d, --description <description>    Add description to new tunnel
  -l, --labels <labels>              Add labels to new tunnel: space separated list of labels that can be used to
                                     search for tunnel
  -p, --port-numbers <port-numbers>  Local server port number(s)
  --protocol <protocol>              Protocol for the port(s): 'http', 'https', or 'auto' (default)
  -e, --expiration <expiration>      Tunnel expiration (hours and days). Use h for hours and d for days
  -a, --allow-anonymous              Allow anonymous client access
  --access-token <access-token>      Host access token
  --host-header <host-header>        Host header value to rewrite in requests forwarded from a web client. Use
                                     "unchanged" to keep the original header, By default Host header is changed to
                                     "localhost".
  --origin-header <origin-header>    Origin header value to rewrite in requests forwarded from a web client. Use
                                     "unchanged" to keep the original header. By default Origin header is changed to
                                     "http(s)://localhost"
  -v, --verbose                      Enable verbose output
  -?, -h, --help                     Show help and usage information



PS C:\ devtunnel host myragbotsla --port-numbers 3978 --protocol https --allow-anonymous
Tunnel service error: Invalid arguments. Batch update of ports is not supported. Add, update, or delete ports individually instead.
Request ID: 51e19983-804c-4669-8818-f168f0b6f317
PS C:\ devtunnel list
Found 1 tunnel.

Tunnel ID                           Host Connections     Labels                    Ports                Expiration                Description
myragbotsla.euw                     0                                              1                    30 days
PS C:\ devtunnel delete myragbotsla
You are about to delete myragbotsla.euw. Are you sure? y/ny
Deleted: myragbotsla.euw
PS C:\ devtunnel create myragbotsla --allow-anonymous
Welcome to dev tunnels!
CLI version: 1.0.1435+d49a94cc24

By using the software, you agree to
  - the dev tunnels License Terms: https://aka.ms/devtunnels/tos
  - the Microsoft Privacy Statement: https://privacy.microsoft.com/privacystatement

Report issues on GitHub: https://aka.ms/devtunnels/issues
Use 'devtunnel --help' to see available commands or visit: https://aka.ms/devtunnels/docs

Tunnel ID             : myragbotsla.euw
Description           :
Labels                :
Access control        : {+Anonymous [connect]}
Host connections      : 0
Client connections    : 0
Current upload rate   : 0 MB/s (limit: 20 MB/s)
Current download rate : 0 MB/s (limit: 20 MB/s)
Tunnel Expiration     : 30 days
