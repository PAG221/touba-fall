from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import date, datetime
import io
import db
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "touba_fall_secret_key_2025")


# -------------------------
# HOME - LISTE COTISATIONS
# -------------------------
@app.route("/")
def home():
    try:
        conn = db.get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cotisations ORDER BY id DESC")
        data = cursor.fetchall()

        conn.close()

        return render_template("login.html", cotisations=data)

    except Exception as e:
        return f"Erreur serveur : {e}"


# -------------------------
# AJOUT COTISATION
# -------------------------
@app.route("/add", methods=["POST"])
def add():
    try:
        date_cotisation = request.form["date"]
        montant = request.form["montant"]

        conn = db.get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO cotisations (date, montant) VALUES (%s, %s)",
            (date_cotisation, montant)
        )

        conn.commit()
        conn.close()

        flash("Cotisation ajoutée avec succès ✔")
        return redirect(url_for("home"))

    except Exception as e:
        return f"Erreur ajout : {e}"


# -------------------------
# SUPPRESSION COTISATION
# -------------------------
@app.route("/delete/<int:id>")
def delete(id):
    try:
        conn = db.get_db()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cotisations WHERE id=%s", (id,))

        conn.commit()
        conn.close()

        flash("Cotisation supprimée ✔")
        return redirect(url_for("home"))

    except Exception as e:
        return f"Erreur suppression : {e}"


# -------------------------
# TEST BASE DE DONNÉES
# -------------------------
@app.route("/test-db")
def test_db():
    try:
        conn = db.get_db()
        conn.close()
        return "Connexion DB OK ✔"
    except Exception as e:
        return f"Erreur DB : {e}"


# -------------------------
# EXPORT PDF (BASIC)
# -------------------------
@app.route("/export")
def export():
    try:
        from reportlab.pdfgen import canvas

        conn = db.get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cotisations")
        data = cursor.fetchall()
        conn.close()

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer)

        pdf.drawString(100, 800, "Touba Fall - Cotisations")

        y = 750
        for row in data:
            pdf.drawString(100, y, f"ID:{row[0]} | Date:{row[1]} | Montant:{row[2]}")
            y -= 20

        pdf.save()
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name="cotisations.pdf")

    except Exception as e:
        return f"Erreur PDF : {e}"


# -------------------------
# RUN LOCAL / RENDER
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
