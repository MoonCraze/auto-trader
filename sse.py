import json
import random
import string
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, render_template_string

# Initialize Flask application
app = Flask(__name__)

# --- Start of Modification ---

# Pool of token addresses to be used
tokens = ["EU1q1FfzCPG9QHZZQvy1fL7vmisWtBApMcaiaWsVpump","HVS5knBKYJ9Xy4WCYEHCrXYJ7Noz2CWLibnMM6Sipump","BM8b4U4cyXCieBRPDAAAygiQwKQemEJntt2yWJ8Jpump","Pz7zD359jya1s9jzp72inqfmKF13ziuJv6HzVfkpump","a3W4qutoEJA4232T2gwZUfgYJTetr96pU4SJMwppump","2G4wNeiRvjRg5dDbD87d9XBVLTFQ3Li9r2qkSey9pump","4SDfM29FFTmQDGKBHtThh9oYhdRcwPSTqYVgJ6EtyLSD","8TuHAfTBTMW1fJNq5bNoeX4zhk2492DNsCgVSYzApump","DkETzNyP4oST2NMU4mmnZwxerh3EESaxtfczk3n3pump","5yMU4CEnjfT37mEaFFnPTWwy1YC23GvVjJxuLzPTpump","EBGJEG6tohUxLWqfoo4c2qdYkEcrkTEWwXpq8LA1pump","63ZtMrbq7dgrQQQiouMXG821GGyTMGkC33BFgDZYpump","AcRNmqhM5AqC2q17cHdQ2DwBj3gwmffcSU2EQySmpump","Gbu7JAKhTVtGyRryg8cYPiKNhonXpUqbrZuCDjfUpump"]

# --- End of Modification ---


def random_string(length=44):
    """Generates a random alphanumeric string of a given length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_events():
    """
    Generates mock server-sent events with correct formatting and keepalives.
    """
    # Send a named 'connected' event
    yield "event: connected\n"
    yield "data: Connection established successfully!\n\n"
    time.sleep(1)

    while True:
        
        # Set up timestamps
        now = datetime.now(timezone.utc)
        window_start = now
        window_end = now + timedelta(seconds=5)
        triggered_at = now + timedelta(seconds=random.uniform(1, 4))

        # Create the data payload
        unique_wallet_count = 4
        data_payload = {
            # --- Start of Modification ---
            # Randomly select one token address from the predefined pool
            "tokenAddress": random.choice(tokens),
            # --- End of Modification ---
            "uniqueWalletCount": unique_wallet_count,
            "walletAddresses": [random_string() for _ in range(unique_wallet_count)],
            "windowStart": window_start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "windowEnd": window_end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "triggeredAt": triggered_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        }
        
        # Yield the named 'data' event in SSE format
        yield "event: data\n"
        yield f"data: {json.dumps(data_payload)}\n\n"
        
        # --- Send several 'keepalive' events (as comments) ---
        # These help keep the connection alive through idle proxies
        for _ in range(5):
            time.sleep(2) # Wait for 2 seconds
            yield ": keepalive\n\n"


@app.route('/stream')
def stream():
    """The route that streams the SSE events with anti-buffering headers."""
    response = Response(generate_events(), mimetype='text/event-stream')
    # Add headers to disable proxy buffering
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/')
def index():
    """A simple HTML page to display the SSE stream with corrected JavaScript."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock SSE Server</title>
        <style>
            body { 
                font-family: 'Courier New', Courier, monospace; 
                background-color: #1e1e1e; 
                color: #d4d4d4;
                line-height: 1.6;
            }
            h1 { color: #569cd6; }
            #events { 
                border: 1px solid #333;
                padding: 15px;
                white-space: pre; /* Use 'pre' to respect newlines in JSON */
                word-wrap: break-word;
            }
            .event-data { color: #9cdcfe; }
            .event-connected { color: #4ec9b0; }
            .event-keepalive { color: #6A9955; }
        </style>
    </head>
    <body>
        <h1>Mock SSE Stream</h1>
        <p>Connecting to <code>/stream</code>...</p>
        <div id="events"></div>
        <script>
            const eventSource = new EventSource("/stream");
            const eventsDiv = document.getElementById('events');

            // Listen for the custom 'connected' event from the server
            eventSource.addEventListener('connected', function(event) {
                const p = document.createElement('p');
                p.className = 'event-connected';
                p.textContent = `: ${event.data}`;
                eventsDiv.appendChild(p);
            });
            
            // Listen for the custom 'data' event from the server
            eventSource.addEventListener('data', function(event) {
                const p = document.createElement('p');
                p.className = 'event-data';
                // Parse and re-format the JSON for better readability
                const dataObject = JSON.parse(event.data);
                p.textContent = 'data: ' + JSON.stringify(dataObject, null, 2); // 2-space indentation
                eventsDiv.appendChild(p);

                // Add keepalive messages visually for demonstration
                for (let i = 0; i < 5; i++) {
                    const p_keep = document.createElement('p');
                    p_keep.className = 'event-keepalive';
                    p_keep.textContent = ': keepalive';
                    eventsDiv.appendChild(p_keep);
                }
            });

            eventSource.onerror = function(err) {
                console.error("EventSource failed:", err);
                const p = document.createElement('p');
                p.style.color = 'red';
                p.textContent = 'Connection lost. Will attempt to reconnect...';
                eventsDiv.appendChild(p);
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == '__main__':
    # Run the Flask app
    # You can access it at http://127.0.0.1:5000 in a local environment
    # or via the forwarded port in GitHub Codespaces.
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)