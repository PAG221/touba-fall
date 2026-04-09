"""
app.py - Application web Flask pour Touba Fall
Gestion des cotisations hebdomadaires - Version Web
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import date, datetime
import io
import db
import os
import mysql.connector

def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT"))
    )

app = Flask(__name__)
app.secret_key = 'touba_fall_secret_key_2025'  # Change this in production

# ─── Configuration ──────────────────────────────────────────────────────────────

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234'

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Page d'accueil - redirection vers login ou dashboard"""
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion administrateur"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Connexion réussie', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Déconnexion"""
    session.pop('logged_in', None)
    flash('Déconnexion réussie', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Tableau de bord principal"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    try:
        # Récupérer les données pour le dashboard
        cotisations = db.get_toutes_cotisations()
        stats = db.get_statistiques()

        # Calculer le total du mois en cours
        auj = date.today()
        total_mois = db.get_total_mois(auj.year, auj.month)

        # Calculer le nombre de semaines (jeudis distincts)
        nb_semaines = stats.get('nb_jeudis', 0)

        return render_template('dashboard.html',
                             cotisations=cotisations,
                             stats=stats,
                             total_mois=total_mois,
                             nb_semaines=nb_semaines,
                             aujourd_hui=str(db.get_jeudi_actuel()))

    except Exception as e:
        flash(f'Erreur lors du chargement des données: {str(e)}', 'error')
        return render_template('dashboard.html', cotisations=[], stats={}, total_mois=0, nb_semaines=0)

@app.route('/add', methods=['POST'])
def add_contribution():
    """Ajouter une nouvelle cotisation"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    try:
        date_str = request.form.get('date', '').strip()
        montant_str = request.form.get('montant', '').strip()

        # Validations
        if not date_str:
            flash('Veuillez saisir une date', 'error')
            return redirect(url_for('dashboard'))

        if not montant_str:
            flash('Veuillez saisir un montant', 'error')
            return redirect(url_for('dashboard'))

        # Conversion et validation
        try:
            date_cot = date.fromisoformat(date_str)
        except ValueError:
            flash('Format de date invalide (AAAA-MM-JJ)', 'error')
            return redirect(url_for('dashboard'))

        try:
            montant = float(montant_str.replace(',', '.'))
            if montant <= 0:
                raise ValueError
        except ValueError:
            flash('Montant invalide (nombre positif requis)', 'error')
            return redirect(url_for('dashboard'))

        # Ajouter à la base de données
        new_id = db.ajouter_cotisation(date_cot, montant)
        flash(f'Cotisation #{new_id} enregistrée avec succès', 'success')

    except Exception as e:
        flash(f'Erreur lors de l\'ajout: {str(e)}', 'error')

    return redirect(url_for('dashboard'))

@app.route('/delete/<int:cotisation_id>', methods=['POST'])
def delete_contribution(cotisation_id):
    """Supprimer une cotisation"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    try:
        success = db.supprimer_cotisation(cotisation_id)
        if success:
            flash('Cotisation supprimée avec succès', 'success')
        else:
            flash('Cotisation introuvable', 'error')
    except Exception as e:
        flash(f'Erreur lors de la suppression: {str(e)}', 'error')

    return redirect(url_for('dashboard'))

@app.route('/export_pdf')
def export_pdf():
    """Exporter les cotisations en PDF"""
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    try:
        # Créer un buffer en mémoire pour le PDF
        buffer = io.BytesIO()

        # Générer le PDF dans le buffer
        n = db.exporter_pdf_to_buffer(buffer)

        buffer.seek(0)

        # Générer le nom du fichier avec la date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"cotisations_touba_fall_{today}.pdf"

        flash(f'PDF généré avec succès ({n} entrées)', 'success')

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        flash(f'Erreur lors de l\'export PDF: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# ─── Fonctions utilitaires ─────────────────────────────────────────────────────

def initialize_app():
    """Initialisation de l'application"""
    print("🔌 Connexion à Touba Fall Database…")
    try:
        db.initialize_database()
        print("✔  Système Touba Fall prêt.")
    except Exception as e:
        print(f"✘ Erreur de connexion à MariaDB: {e}")
        print("Vérifiez que MariaDB est démarré et que les paramètres dans db.py sont corrects.")
        exit(1)

# ─── Lancement ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    initialize_app()
    print("🚀 Démarrage du serveur web Touba Fall…")
    print("Accédez à l'application sur: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
