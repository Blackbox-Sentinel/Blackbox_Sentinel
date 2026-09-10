import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# Check if the pipeline worker thread is alive by looking at ALL journal entries since restart
print("=== ALL GUI LOGS SINCE LAST RESTART ===")
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S journalctl -u gui.service --since "2026-09-11 02:17:00" --no-pager 2>&1 | grep -i -E "thread|exception|error|traceback|pipeline|anomaly|mqtt"')
out = stdout.read().decode('utf-8', errors='replace')
print(out if out.strip() else "(no matching entries)")

# Check the thread state directly - see if background threads are alive
print("\n=== CHECKING THREAD STATES ===")
stdin, stdout, stderr = client.exec_command("python3 -c \"import subprocess; r=subprocess.run(['ls', '-la', '/proc/2899/task/'], capture_output=True, text=True); print(r.stdout); print('Thread count:', len(r.stdout.strip().split(chr(10)))-1)\"")
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out)
if err: print("ERR:", err)

client.close()
