from flask import Flask, render_template, request, redirect, url_for
import sqlalchemy

app = Flask(__name__)

groups = {


}

@app.route('/create_group', methods=['POST'])
def create_group():
    name = request.form['name']
    group_id=str(len(groups) + 1)
    groups[group_id]= {
        'name': name,
        'expenses': [],
        'members': []
    }
    return redirect(f'/group/{group_id}')

@app.route('/group/<group_id>/add_expense', methods=['POST'])
def add_expense(group_id):
    paid_by = request.form['paid_by']
    amount = float(request.form['amount'])
    description = request.form['description']
    split_between = request.form.getlist('split_between')
    if not split_between:
        split_between = [paid_by]
    if paid_by not in groups[group_id]['members']: #find out why can double group
        groups[group_id]['members'].append(paid_by)

    for person in split_between:
        if person not in groups[group_id]['members']:
            groups[group_id]['members'].append(person)

    expense = {
        'paid_by': paid_by,
        'amount': amount,
        'description': description,
        'split_between': split_between
    }
    groups[group_id]['expenses'].append(expense)
    return redirect(f'/group/{group_id}')

def calculate_balances(group_id):
    balances = {}
    group = groups[group_id]

    for member in group['members']:
        balances[member] = 0

    for expense in group['expenses']:
        paid_by = expense['paid_by']
        amount = expense['amount']
        split_between = expense['split_between']
        split_amount = amount / len(split_between)

        balances[paid_by] += amount
        for person in split_between:
            balances[person] -= split_amount
    return balances

@app.route('/group/<group_id>')
def view_group(group_id):
    if group_id not in groups:
        return redirect('/')
    group = groups[group_id]
    balances = calculate_balances(group_id)
    return render_template('group.html',
                            group=group,
                            balances=balances,
                            group_id=group_id)

@app.route('/')
def home():
    return render_template('index.html', groups=groups)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9987, debug=True)

