from flask import Flask, render_template

app = Flask(__name__, static_folder='static')
app.config["TEMPLATES_AUTO_RELOAD"] = True

DUMMY_DATA = {
    "site_no": "1163",
    "mater_name": "SAMPLE MATERIAL",
    "supply_name": "",
    "plt_type": "MASTER BATCH",
    "plt_no": "MB-20261113-001",
    "qty": "1250",
    "mater_no": "MAT-98765",
    "check_result": "OK",
    "barcode": "8801234567890",
    "prod_date": "2026-11-13 08:30:00",
    "valid_date": "2026-11-13 10:45:00",
    "usr_id": "OPERATOR01"
}

class Data:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)

@app.route("/")
def display1():
    return render_template("display1.html", site="1163", data=Data(DUMMY_DATA), api_prefix="/info")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
