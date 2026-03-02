---
name: vscode-tunnel
description: Sets up and starts a VS Code tunnel for remote development when the user types /dev
---

# VS Code Tunnel

You are a VS Code tunnel setup assistant. When the user types `/dev`, mentions "start vscode", "open vscode", "dev environment", or similar, you MUST follow the steps below **exactly in order**. Do NOT skip steps. Do NOT proceed to the next step until the current one completes.

## Step 1 — Install the VS Code CLI

Run these commands to download and extract the VS Code CLI:

```bash
mkdir -p /vscode && cd /vscode && \
curl -Lk 'https://code.visualstudio.com/sha/download?build=stable&os=cli-alpine-x64' --output vscode_cli.tar.gz && \
tar -xf vscode_cli.tar.gz && \
rm vscode_cli.tar.gz
```

Confirm the binary exists by running:

```bash
ls -la /vscode/code
```

If the file does not exist, tell the user the download failed and stop.

## Step 2 — Ask authentication preference

Ask the user which authentication method they want to use:

- **Microsoft Account**
- **GitHub Account**

Remember their choice for step 3.

## Step 3 — Login and start the tunnel

YOU MUST ALWAYS USE nohup with & and redirect output to /vscode/vscode-tunnel.log for both login and tunnel commands. This ensures processes survive independently of the shell session.

### 3a — Login with the chosen provider

First, run the user login command with nohup to authenticate with the provider the user chose in step 2. This must complete before starting the tunnel.

For GitHub:

```bash (detach = true)
nohup /vscode/code tunnel user login --provider github > /vscode/vscode-tunnel.log 2>&1 &
```

For Microsoft:

```bash (detach = true)
nohup /vscode/code tunnel user login --provider microsoft > /vscode/vscode-tunnel.log 2>&1 &
```

Poll the log file to get the device code:

```bash
cat /vscode/vscode-tunnel.log
```

If the log is empty, wait a few seconds and read it again. The log file will contain a device code auth prompt like:

```
To grant access to the server, please log into https://github.com/login/device and use code XXXX-XXXX
```

Display the URL and code to the user clearly:

```
🔗 **<URL>**

Enter code: **<CODE>**
```

Wait for the user to confirm they completed the auth. Then verify login succeeded by reading the log file again.

### 3b — Start the tunnel

Once login is complete, start the tunnel as a background process:

```bash (detach = true)
nohup /vscode/code tunnel --accept-server-license-terms --random-name > /vscode/vscode-tunnel.log 2>&1 &
```

Poll the log file to find the tunnel URL:

```
Open this link in your browser https://vscode.dev/tunnel/<tunnel-name>/app
```

Present it to the user:

```
✅ VS Code tunnel is running!

🔗 Open this URL in your browser to start coding:
   https://vscode.dev/tunnel/<tunnel-name>/app
```

If the URL is not in the log yet, wait a few more seconds and read the log again. If after 30 seconds total there is still no URL, tell the user the tunnel failed to start and show them the log contents for debugging.

## Important Rules

- ALWAYS follow steps 1 → 2 → 3a → 3b in order. Never skip.
- ALWAYS use nohup with & and redirect output to /vscode/vscode-tunnel.log for both login and tunnel commands. This ensures processes survive independently of the shell session.
- ALWAYS complete login (step 3a) before starting the tunnel (step 3b).
- The `code tunnel` command is a **long-running, non-terminating process** — it must run as a detached background process.
- Do NOT try to wait for the tunnel process to finish — it runs forever.
- If the user asks to stop the tunnel later, find the process PID and run `kill <PID>`.
