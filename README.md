# ALX Backend GraphQL CRM

A minimal Django + Graphene project implementing a CRM with GraphQL queries, mutations, and advanced filtering.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py shell -c "import seed_db; seed_db.run()"
python manage.py runserver
```

Open http://localhost:8000/graphql and try:

```graphql
{
  hello
}
```

Then run the mutations provided in your assignment.
