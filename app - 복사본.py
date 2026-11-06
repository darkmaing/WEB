from flask import Flask, request, render_template, redirect, url_for
from flask_cors import CORS
import oracledb
from time import time

# Oracle Instant Client (Thick mode)
oracledb.init_oracle_client(lib_dir=r"D:\instantclient_11_2")

app = Flask(__name__, static_folder='static')
CORS(app)

# Connection Pool
pool = oracledb.create_pool(
    user="sid20014",
    password="sid20014",
    dsn="172.204.23.1:1521/orcl",
    min=2,
    max=10,
    increment=1
)

# =========================
# 초기 선택 화면
# =========================
@app.route("/")
def select():
    return render_template("select.html")

# =========================
# 선택 후 분기
# =========================
@app.route("/display", methods=["POST"])
def display():
    sites = request.form.getlist("site")
    print("선택된 사이트:", sites)

    if len(sites) == 2:
        left_site = sites[0]
        right_site = sites[1]

        left_data = get_tabdsp_cached(left_site)
        right_data = get_tabdsp_cached(right_site)

        return render_template(
            "display2.html",
            left_site=left_site,
            right_site=right_site,
            left=left_data,
            right=right_data
        )

    elif len(sites) == 1:
        data = get_tabdsp_cached(sites[0])
        return render_template(
            "display1.html",
            site=sites[0],
            data=data
        )

    return redirect(url_for("select"))
# =========================
# 사이트별 DB 조회 (HTML용)
# =========================
def get_tabdsp(site_no):
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

    with pool.acquire() as conn:
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



CACHE = {}
CACHE_TTL = 5  # 5초

def get_tabdsp_cached(site_no):
    now = time()

    if site_no in CACHE:
        data, ts = CACHE[site_no]
        if now - ts < CACHE_TTL:
            return data

    data = get_tabdsp(site_no)
    CACHE[site_no] = (data, now)
    return data

# =========================
# (선택) JSON API가 필요할 때만 사용
# =========================
@app.route("/api/site/<site_id>")
def site_api(site_id):
    data = get_tabdsp(site_id)
    if data:
        return data
    return {"error": "사이트 번호 없음"}

@app.route("/api/display1/<site_id>")
def api_display1(site_id):
    data = get_tabdsp_cached(site_id)
    if data:
        return data
    return {}

@app.route("/api/display2")
def api_display2():
    left_site = request.args.get("left")
    right_site = request.args.get("right")

    result = {}

    if left_site:
        result["left"] = get_tabdsp_cached(left_site)

    if right_site:
        result["right"] = get_tabdsp_cached(right_site)

    return result


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)