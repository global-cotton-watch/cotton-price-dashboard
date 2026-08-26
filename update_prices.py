import json

from cotton_dashboard.service import update_all
from cotton_dashboard.web import create_app

app = create_app()
with app.app_context():
    result = update_all(app.extensions["price_store"])
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["status"] in {"success", "partial"} else 1)
