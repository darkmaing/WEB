from flask import Flask, request, render_template, redirect, url_for
from flask_cors import CORS
import oracledb
import json
from time import time

# oracledb.init_oracle_client(lib_dir=r'D:\\instantclient_11_2')

app = Flask(__name__, static_folder='static')
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
CORS(app)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# config.json?먯꽌 DB ?뺣낫 諛??ъ씠??紐⑸줉 濡쒕뱶
with open(r"D:\instantclient_11_2\config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# config.json??db_user, db_password, db_dsn???쎌뼱??? ?앹꽦
pools = {}
for app_type, cfg in CONFIG.items():
    pools[app_type] = oracledb.create_pool(
        user=cfg["db_user"],
        password=cfg["db_password"],
        dsn=cfg["db_dsn"],
        min=2,
        max=10,
        increment=1
    )

CACHE = {t: {} for t in CONFIG}
CACHE_TTL = 5


@app.route("/")
def index():
    first = list(CONFIG.keys())[0]
    return redirect(url_for("select", app_type=first.lower()))


@app.route("/<app_type>/")
def select(app_type):
    key = app_type.upper()
    if key not in CONFIG:
        return "Not Found", 404
    cfg = CONFIG[key]
    return render_template("select.html",
        app_type=app_type.lower(),
        sites=cfg["sites"],
        action_url=f"/{app_type.lower()}/display"
    )


@app.route("/<app_type>/display", methods=["POST"])
def display(app_type):
    key = app_type.upper()
    if key not in CONFIG:
        return "Not Found", 404

    sites = request.form.getlist("site")
    api_prefix = f"/{app_type.lower()}"

    if len(sites) == 2:
        left_data = get_tabdsp_cached(key, sites[0])
        right_data = get_tabdsp_cached(key, sites[1])
        return render_template("display2.html",
            left_site=sites[0],
            right_site=sites[1],
            left=left_data,
            right=right_data,
            api_prefix=api_prefix
        )
    elif len(sites) == 1:
        data = get_tabdsp_cached(key, sites[0])
        return render_template("display1.html",
            site=sites[0],
            data=data,
            api_prefix=api_prefix
        )

    return redirect(url_for("select", app_type=app_type.lower()))


def get_tabdsp(app_type, site_no):
    sql = """
        SELECT
            SITE_NO,
            MATER_NAME,
            PLT_NO,
            PLT_TYPE,
            QTY,
            MATER_NO,
            BARCODE,
            MAX_TIME,
            USR_ID,
            PRODUCT_DATE,
            CASE
                WHEN CHECK_RESULT = 1 THEN 'OK'
                WHEN CHECK_RESULT = 0 THEN 'NG'
                ELSE 'N/A'
            END AS CHECK_RESULT
        FROM TABDSP
        WHERE SITE_NO = :site_no
    """
    with pools[app_type].acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, site_no=int(site_no))
            row = cur.fetchone()
            if not row:
                return None
            plt_type_map = {"MB": "MASTER BATCH", "FB": "FINAL BATCH"}
            return {
                "site_no": row[0],
                "mater_name": row[1],
                "plt_no": row[2],
                "plt_type": plt_type_map.get(row[3], row[3] or ""),
                "qty": row[4],
                "mater_no": row[5],
                "barcode": row[6],
                "valid_date": row[7] if row[7] else "",
                "usr_id": row[8],
                "prod_date": row[9],
                "check_result": row[10] or "N/A"
            }


def get_tabdsp_cached(app_type, site_no):
    now = time()
    cache = CACHE[app_type]
    if site_no in cache:
        data, ts = cache[site_no]
        if now - ts < CACHE_TTL:
            return data
    data = get_tabdsp(app_type, site_no)
    cache[site_no] = (data, now)
    return data


@app.route("/<app_type>/api/display1/<site_id>")
def api_display1(app_type, site_id):
    key = app_type.upper()
    if key not in CONFIG:
        return {}
    data = get_tabdsp_cached(key, site_id)
    return data if data else {}


@app.route("/<app_type>/api/display2")
def api_display2(app_type):
    key = app_type.upper()
    if key not in CONFIG:
        return {}
    left_site = request.args.get("left")
    right_site = request.args.get("right")
    result = {}
    if left_site:
        result["left"] = get_tabdsp_cached(key, left_site)
    if right_site:
        result["right"] = get_tabdsp_cached(key, right_site)
    return result


@app.route("/preview/display1")
def preview_display1():
    dummy = {
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
    return render_template("display1.html", site="1163", data=type("D", (), dummy)(), api_prefix="/info")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

