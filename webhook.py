import subprocess
import os
from flask import Flask, request, jsonify
import hmac
import hashlib

webhook_app = Flask(__name__)

# Secret key for webhook security (optional but recommended)
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-secret-key')

@webhook_app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Optional: Verify webhook signature for security
        signature = request.headers.get('X-Hub-Signature-256')
        if signature and WEBHOOK_SECRET:
            payload = request.get_data()
            expected_signature = 'sha256=' + hmac.new(
                WEBHOOK_SECRET.encode(), payload, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                return jsonify({'error': 'Invalid signature'}), 403

        # Deploy commands
        deploy_commands = [
            'cd /home/hieunguyenhanu/Roomate-Cost-Splitter',
            'git pull origin main',
            'source /home/hieunguyenhanu/.virtualenvs/flaskenv/bin/activate',
            'pip install -r requirements.txt',
            'touch /var/www/hieunguyenhanu_pythonanywhere_com_wsgi.py'
        ]
        
        # Execute commands
        result = subprocess.run(
            ' && '.join(deploy_commands),
            shell=True,
            capture_output=True,
            text=True,
            cwd='/home/hieunguyenhanu/Roomate-Cost-Splitter'
        )
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': 'Deployment completed successfully',
                'output': result.stdout
            }), 200
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Deployment failed',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    webhook_app.run(host='0.0.0.0', port=5001, debug=True)
