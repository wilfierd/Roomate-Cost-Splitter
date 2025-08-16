from flask import Flask, render_template, request, jsonify
import subprocess
import os
import hmac
import hashlib

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
	try:
		data = request.json
		total_rent = float(data['total'])
		shared_purchases = data['sharedPurchases']
		transfers = data['transfers']
		custom_expenses = data.get('customExpenses', [])

		# First, subtract custom expenses from total rent
		custom_expenses_total = sum(float(expense['amount']) for expense in custom_expenses)
		base_rent = total_rent - custom_expenses_total
		
		# Base amount each person should pay (exactly 1/3 of base rent)
		base_per_person = base_rent / 3
		
		# Initialize balances and track breakdown details
		balances = {
			'tiep': -base_per_person,
			'hieu': -base_per_person,
			'hai': -base_per_person
		}
		
		# Initialize breakdown of adjustments with base amount
		breakdown = {
			'tiep': [{'description': f'Base share (1/3 of rent, excluding custom expenses)', 'amount': f"-{int(base_per_person):,}"}],
			'hieu': [{'description': f'Base share (1/3 of rent, excluding custom expenses)', 'amount': f"-{int(base_per_person):,}"}],
			'hai': [{'description': f'Base share (1/3 of rent, excluding custom expenses)', 'amount': f"-{int(base_per_person):,}"}]
		}

		# Process shared purchases
		for i, purchase in enumerate(shared_purchases):
			amount = float(purchase['amount'])
			purchaser = purchase['by']
			per_person_share = amount / 3
			
			# Purchaser paid full amount but only owes their share
			credit = amount - per_person_share
			balances[purchaser] += credit
			breakdown[purchaser].append({
				'description': f"Shared purchase #{i+1} credit ({amount:,} VND - share)",
				'amount': f"+{int(credit):,}"
			})
			
			# Others owe their share
			for person in balances:
				if person != purchaser:
					balances[person] -= per_person_share
					breakdown[person].append({
						'description': f"Share of purchase #{i+1} by {purchaser}",
						'amount': f"-{int(per_person_share):,}"
					})

		# Process custom split expenses (like elevator service)
		for i, expense in enumerate(custom_expenses):
			amount = float(expense['amount'])
			description = expense['description']
			
			# Get who uses this expense
			tiep_uses = expense.get('tiepUses', False)
			hieu_uses = expense.get('hieuUses', False)
			hai_uses = expense.get('haiUses', False)
			
			# Count users
			users_count = sum([tiep_uses, hieu_uses, hai_uses])
			if users_count == 0:
				# Nobody uses this? Skip or handle as error
				continue
				
			# Calculate per-user share
			per_user_share = amount / users_count
			
			# Each person who uses this pays their share
			if tiep_uses:
				balances['tiep'] -= per_user_share
				breakdown['tiep'].append({
					'description': f"Share of {description} (split among {users_count} users)",
					'amount': f"-{int(per_user_share):,}"
				})
			
			if hieu_uses:
				balances['hieu'] -= per_user_share
				breakdown['hieu'].append({
					'description': f"Share of {description} (split among {users_count} users)",
					'amount': f"-{int(per_user_share):,}"
				})
			
			if hai_uses:
				balances['hai'] -= per_user_share
				breakdown['hai'].append({
					'description': f"Share of {description} (split among {users_count} users)",
					'amount': f"-{int(per_user_share):,}"
				})

		# Process transfers - when A transfers to B, it means A owes B money
		for i, transfer in enumerate(transfers):
			amount = float(transfer['amount'])
			from_person = transfer['from']  # Person who owes money
			to_person = transfer['to']      # Person who is owed money
			
			# From_person pays more (debit)
			balances[from_person] -= amount
			breakdown[from_person].append({
				'description': f"Debt owed to {to_person}",
				'amount': f"-{int(amount):,}"
			})
			
			# To_person pays less (credit)
			balances[to_person] += amount
			breakdown[to_person].append({
				'description': f"Credit from {from_person}'s debt",
				'amount': f"+{int(amount):,}"
			})
		
		# Calculate final amounts to pay (negative balance = amount to pay)
		final_payments = {
			'tiep': -balances['tiep'],
			'hieu': -balances['hieu'],
			'hai': -balances['hai']
		}

		# Adjust the total check to ensure it equals the original total rent
		adjustment_needed = total_rent - sum(final_payments.values())
		if abs(adjustment_needed) > 0.01:
			# Add a small adjustment to the first person with a non-zero percentage
			# This ensures the total adds up exactly
			for person in ['tiep', 'hieu', 'hai']:
				final_payments[person] += adjustment_needed
				breakdown[person].append({
					'description': 'Rounding adjustment',
					'amount': f"{'+' if adjustment_needed < 0 else '-'}{abs(int(adjustment_needed)):,}"
				})
				break

		# Prepare results with breakdown
		results = {
			'total_rent': f"{int(total_rent):,}",
			'base_rent': f"{int(base_rent):,}",
			'tiep_final': f"{int(final_payments['tiep']):,}",
			'hieu_final': f"{int(final_payments['hieu']):,}",
			'hai_final': f"{int(final_payments['hai']):,}",
			'total_check': f"{int(sum(final_payments.values())):,}",
			'tiep_breakdown': breakdown['tiep'],
			'hieu_breakdown': breakdown['hieu'],
			'hai_breakdown': breakdown['hai']
		}

		return jsonify(results)
	except Exception as e:
		return jsonify({'error': str(e)}), 400

# Webhook endpoint for GitHub Actions
@app.route('/webhook', methods=['POST'])
def webhook():
	try:
		# Optional: Verify webhook signature for security
		WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-secret-key')
		signature = request.headers.get('X-Hub-Signature-256')
		
		# DEBUG: Log signature details
		payload = request.get_data()
		print(f"Received signature: {signature}")
		print(f"Webhook secret: {WEBHOOK_SECRET}")
		print(f"Payload: {payload}")
		
		# TEMPORARY: Skip signature verification for testing
		# if signature and WEBHOOK_SECRET and signature != 'sha256=test':
		# 	expected_signature = 'sha256=' + hmac.new(
		# 		WEBHOOK_SECRET.encode(), payload, hashlib.sha256
		# 	).hexdigest()
		# 	print(f"Expected signature: {expected_signature}")
		# 	if not hmac.compare_digest(signature, expected_signature):
		# 		return jsonify({'error': 'Invalid signature', 'received': signature, 'expected': expected_signature}), 403

		# Simplified deployment - just git pull and touch wsgi
		try:
			# Git pull
			git_result = subprocess.run(['git', 'pull', 'origin', 'main'], 
				capture_output=True, text=True, cwd='/home/hieunguyenhanu/Roomate-Cost-Splitter')
			
			# Touch WSGI file to reload
			subprocess.run(['touch', '/var/www/hieunguyenhanu_pythonanywhere_com_wsgi.py'])
			
			result = git_result  # Use git result for response
		except Exception as e:
			return jsonify({'status': 'error', 'message': str(e)}), 500
		
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
	app.run(host='0.0.0.0', debug=True) 