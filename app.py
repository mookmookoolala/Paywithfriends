from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import create_database, database_exists
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# MySQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



# Models
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    expenses = db.relationship('Expense', backref='group', lazy=True)
    members = db.relationship('Member', backref='group', lazy=True)

    def get_total_spent(self):
        return sum(expense.amount for expense in self.expenses)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    splits = db.relationship('Split', backref='expense', lazy=True)

class Split(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    member_name = db.Column(db.String(100), nullable=False)

# Routes
@app.route('/create_group', methods=['POST'])
def create_group():
    name = request.form['name']
    new_group = Group(name=name)
    db.session.add(new_group)
    db.session.commit()
    return redirect(f'/group/{new_group.id}')

@app.route('/group/<int:group_id>/add_expense', methods=['POST'])
def add_expense(group_id):
    paid_by = request.form['paid_by']
    amount = float(request.form['amount'])
    description = request.form['description']
    split_between = request.form.getlist('split_between')

    if not split_between:
        split_between = [paid_by]

    # Create expense
    expense = Expense(
        description=description,
        amount=amount,
        paid_by=paid_by,
        group_id=group_id
    )
    db.session.add(expense)

    # Create member if doesn't exist
    existing_members = Member.query.filter_by(group_id=group_id).all()
    existing_names = [m.name for m in existing_members]

    # Add payer if new
    if paid_by not in existing_names:
        new_member = Member(name=paid_by, group_id=group_id)
        db.session.add(new_member)

    # Add split members if new
    for person in split_between:
        if person not in existing_names:
            new_member = Member(name=person, group_id=group_id)
            db.session.add(new_member)
        
        # Create split record
        split = Split(expense=expense, member_name=person)
        db.session.add(split)

    db.session.commit()
    return redirect(f'/group/{group_id}')

def calculate_balances(group_id):
    balances = {}
    group = Group.query.get(group_id)
    
    # Initialize balances
    for member in group.members:
        balances[member.name] = 0
    
    # Calculate from expenses
    for expense in group.expenses:
        paid_by = expense.paid_by
        amount = expense.amount
        split_between = [split.member_name for split in expense.splits]
        split_amount = amount / len(split_between)
        
        balances[paid_by] += amount
        for person in split_between:
            balances[person] -= split_amount
            
    return balances

@app.route('/group/<int:group_id>')
def view_group(group_id):
    group = Group.query.get_or_404(group_id)
    balances = calculate_balances(group_id)
    total_spent = group.get_total_spent()
    return render_template('group.html',
                         group=group,
                         balances=balances,
                         total_spent=total_spent,
                         group_id=group_id)

@app.route('/')
def home():
    groups = Group.query.all()
    return render_template('index.html', groups=groups)

@app.route('/check')
def check():
    groups = Group.query.all()
    output = {}
    for group in groups:
        output[group.id] = {
            'name': group.name,
            'members': [m.name for m in group.members],
            'expenses': [{
                'description': e.description,
                'amount': e.amount,
                'paid_by': e.paid_by,
                'split_between': [s.member_name for s in e.splits]
            } for e in group.expenses]
        }
    return str(output)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=9987, debug=True)
