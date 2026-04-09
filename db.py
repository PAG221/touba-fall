"""
db.py - Module de gestion de la base de données MariaDB
Application Touba Fall - Gestion des cotisations hebdomadaires
"""

import mysql.connector
from mysql.connector import Error
from datetime import date, timedelta, datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
import io


# ─── Configuration de la base de données ───────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",          # ← Modifier selon votre config
    "password": "",          # ← Modifier selon votre config
    "database": "touba_fall_db",
    "charset": "utf8mb4",
    "autocommit": False,
}


def get_connection():
    """Établit et retourne une connexion à MariaDB."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        raise ConnectionError(f"Impossible de se connecter à MariaDB : {e}")


def initialize_database():
    """
    Crée la base de données et la table si elles n'existent pas.
    À appeler au démarrage de l'application.
    """
    try:
        # Connexion sans spécifier la base (pour la créer si besoin)
        config_sans_db = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conn = mysql.connector.connect(**config_sans_db)
        cursor = conn.cursor()

        # Création de la base de données
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{DB_CONFIG['database']}`")

        # Création de la table cotisations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotisations (
                id       INT AUTO_INCREMENT PRIMARY KEY,
                date     DATE           NOT NULL,
                montant  DECIMAL(10,2)  NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Error as e:
        raise RuntimeError(f"Erreur d'initialisation de la base : {e}")


# ─── CRUD ──────────────────────────────────────────────────────────────────────

def ajouter_cotisation(date_cot: date, montant: float) -> int:
    """
    Insère une nouvelle cotisation.
    Retourne l'ID généré.
    """
    sql = "INSERT INTO cotisations (date, montant) VALUES (%s, %s)"
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (date_cot, montant))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return new_id
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"Erreur lors de l'ajout : {e}")
    finally:
        conn.close()


def supprimer_cotisation(cotisation_id: int) -> bool:
    """Supprime une cotisation par son ID."""
    sql = "DELETE FROM cotisations WHERE id = %s"
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (cotisation_id,))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        return affected > 0
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"Erreur lors de la suppression : {e}")
    finally:
        conn.close()


def get_toutes_cotisations() -> list[dict]:
    """Retourne toutes les cotisations triées par date décroissante."""
    sql = "SELECT id, date, montant FROM cotisations ORDER BY date DESC, id DESC"
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Error as e:
        raise RuntimeError(f"Erreur lors de la récupération : {e}")
    finally:
        conn.close()


def get_cotisations_du_mois(annee: int, mois: int) -> list[dict]:
    """Retourne les cotisations d'un mois donné."""
    sql = """
        SELECT id, date, montant
        FROM cotisations
        WHERE YEAR(date) = %s AND MONTH(date) = %s
        ORDER BY date ASC
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (annee, mois))
        rows = cursor.fetchall()
        cursor.close()
        return rows
    except Error as e:
        raise RuntimeError(f"Erreur récupération du mois : {e}")
    finally:
        conn.close()


# ─── Statistiques ──────────────────────────────────────────────────────────────

def get_statistiques() -> dict:
    """Calcule et retourne les statistiques globales."""
    sql = """
        SELECT
            COUNT(*)                        AS nb_cotisations,
            COUNT(DISTINCT date)            AS nb_jeudis,
            COALESCE(SUM(montant),  0)      AS total,
            COALESCE(AVG(montant),  0)      AS moyenne,
            COALESCE(MIN(montant),  0)      AS minimum,
            COALESCE(MAX(montant),  0)      AS maximum
        FROM cotisations
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        stats = cursor.fetchone()
        cursor.close()
        return stats
    except Error as e:
        raise RuntimeError(f"Erreur statistiques : {e}")
    finally:
        conn.close()


def get_total_mois(annee: int, mois: int) -> float:
    """Retourne le total des cotisations pour un mois donné."""
    sql = """
        SELECT COALESCE(SUM(montant), 0) AS total
        FROM cotisations
        WHERE YEAR(date) = %s AND MONTH(date) = %s
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (annee, mois))
        row = cursor.fetchone()
        cursor.close()
        return float(row["total"]) if row else 0.0
    except Error as e:
        raise RuntimeError(f"Erreur total mois : {e}")
    finally:
        conn.close()


# ─── Export CSV ────────────────────────────────────────────────────────────────

def exporter_pdf(chemin_fichier: str) -> int:
    """
    Exporte toutes les cotisations dans un fichier PDF professionnel.
    Retourne le nombre de lignes exportées.
    """
    cotisations = get_toutes_cotisations()
    
    # Configuration du document
    doc = SimpleDocTemplate(
        chemin_fichier, 
        pagesize=A4,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()

    # Style Titre et texte
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    # En-tête
    elements.append(Paragraph("Touba Fall", title_style))
    elements.append(Paragraph("Rapport détaillé des cotisations hebdomadaires", styles['Heading2']))
    elements.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Préparation des données du tableau
    data = [["ID", "Date", "Montant (FCFA)"]]
    total_somme = 0
    for row in cotisations:
        data.append([
            f"#{row['id']}",
            str(row['date']),
            f"{float(row['montant']):,.0f}"
        ])
        total_somme += float(row['montant'])

    # Construction du tableau (Style Noir & Blanc)
    table = Table(data, colWidths=[60, 180, 180])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 30))

    # Résumé
    elements.append(Paragraph(f"<b>Nombre d'entrées :</b> {len(cotisations)}", styles['Normal']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>TOTAL DES COTISATIONS :</b> {total_somme:,.0f} FCFA", styles['Heading3']))

    doc.build(elements)
    return len(cotisations)


def exporter_pdf_to_buffer(buffer: io.BytesIO) -> int:
    """
    Exporte toutes les cotisations dans un buffer PDF pour le web.
    Retourne le nombre de lignes exportées.
    """
    cotisations = get_toutes_cotisations()
    
    # Configuration du document
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
    )
    elements = []
    styles = getSampleStyleSheet()

    # Style Titre et texte
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=20
    )

    # En-tête
    elements.append(Paragraph("Touba Fall", title_style))
    elements.append(Paragraph("Rapport détaillé des cotisations hebdomadaires", styles['Heading2']))
    elements.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 24))

    # Préparation des données du tableau
    data = [["ID", "Date", "Montant (FCFA)"]]
    total_somme = 0
    for row in cotisations:
        data.append([
            f"#{row['id']}",
            str(row['date']),
            f"{float(row['montant']):,.0f}"
        ])
        total_somme += float(row['montant'])

    # Construction du tableau (Style Noir & Blanc)
    table = Table(data, colWidths=[60, 180, 180])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 30))

    # Résumé
    elements.append(Paragraph(f"<b>Nombre d'entrées :</b> {len(cotisations)}", styles['Normal']))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(f"<b>TOTAL DES COTISATIONS :</b> {total_somme:,.0f} FCFA", styles['Heading3']))

    doc.build(elements)
    return len(cotisations)
    """
    Retourne la date du jeudi de la semaine en cours.
    Si on est après jeudi, retourne le jeudi de cette semaine quand même.
    """
    aujourd_hui = date.today()
    # weekday(): lundi=0 … jeudi=3 … dimanche=6
    jours_jusqu_jeudi = (3 - aujourd_hui.weekday()) % 7
    if jours_jusqu_jeudi == 0:
        return aujourd_hui
    # Si on est avant jeudi → jeudi prochain
    # Si on est après jeudi → jeudi dernier
    if aujourd_hui.weekday() < 3:
        return aujourd_hui + timedelta(days=jours_jusqu_jeudi)
    else:
        return aujourd_hui - timedelta(days=aujourd_hui.weekday() - 3)
