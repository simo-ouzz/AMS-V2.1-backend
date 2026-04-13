#!/bin/bash
# Writes seed_data.py into the running ams_django container and runs it
set -e

echo "Injecting seed_data.py into ams_django container..."

docker exec -i ams_django sh -c 'cat > /app/apps/masterdata/management/commands/seed_data.py' << 'PYEOF'
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone
from masterdata.models import (
    Compte, UserWeb, Personne, categorie, produit, nature, fournisseur,
    marque, departement, location, zone, emplacement, type_tag, tag,
    tagEmplacement, operation, article, item, Fichier,
    TransferHistorique, operation_article, inventaire,
    inventaire_emplacement, detail_inventaire, ArchiveItem,
    TagHistory, TagHistoryEmplacement,
)


def rand_date(start_year=2023, end_year=2026):
    start = date(start_year, 1, 1)
    end = date(end_year, 3, 1)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def rand_dt(start_year=2023, end_year=2026):
    d = rand_date(start_year, end_year)
    return timezone.make_aware(
        timezone.datetime(d.year, d.month, d.day, random.randint(8, 18), random.randint(0, 59))
    )


class Command(BaseCommand):
    help = "Populate AMS database with realistic test data for all tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Delete all existing data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write(self.style.WARNING("Flushing existing data..."))
            for model in [
                detail_inventaire, inventaire_emplacement, inventaire,
                TagHistoryEmplacement, TagHistory, ArchiveItem,
                operation_article, TransferHistorique, item, article,
                Fichier, tagEmplacement, tag, operation, type_tag,
                emplacement, zone, location, departement, marque,
                fournisseur, nature, produit, categorie, Personne,
                UserWeb, Compte,
            ]:
                model.objects.all().delete()
            self.stdout.write("Flushed.")

        self.stdout.write(self.style.MIGRATE_HEADING("Seeding AMS database..."))

        comptes_data = [
            ("Prolog Maroc", "CPT-PROLOG"),
            ("Smatch Digital", "CPT-SMATCH"),
            ("Atlas Logistics", "CPT-ATLAS"),
        ]
        comptes = []
        for libelle, code in comptes_data:
            obj, _ = Compte.objects.get_or_create(libelle=libelle, defaults={"code_compte": code})
            comptes.append(obj)
        self.stdout.write(f"  Comptes: {len(comptes)}")

        compte_main = comptes[0]

        grp_admin, _ = Group.objects.get_or_create(id=1, defaults={"name": "Administrateur"})
        grp_oper, _ = Group.objects.get_or_create(id=2, defaults={"name": "user operateur"})
        grp_spect, _ = Group.objects.get_or_create(id=3, defaults={"name": "User spectateur"})

        users_data = [
            ("admin@smatch.ma", "Admin", "Prolog", "Administrateur", "web", True, compte_main, [grp_admin]),
            ("khalid.benali@smatch.ma", "Khalid", "Benali", "Administrateur", "web", True, compte_main, [grp_admin]),
            ("sara.elmoudir@smatch.ma", "Sara", "El Moudir", "user", "web", False, compte_main, [grp_oper]),
            ("youssef.amrani@smatch.ma", "Youssef", "Amrani", "user", "web", False, compte_main, [grp_oper]),
            ("fatima.zahra@smatch.ma", "Fatima Zahra", "Idrissi", "user", "web", False, compte_main, [grp_spect]),
            ("mehdi.tazi@smatch.ma", "Mehdi", "Tazi", "user", "mobile", False, compte_main, [grp_oper]),
            ("amina.berrada@smatch.ma", "Amina", "Berrada", "user", "mobile", False, compte_main, [grp_oper]),
            ("omar.fassi@smatch.ma", "Omar", "Fassi", "user", "web", False, comptes[1], [grp_spect]),
            ("leila.chaoui@smatch.ma", "Leila", "Chaoui", "Administrateur", "web", True, comptes[1], [grp_admin]),
            ("rachid.bennani@smatch.ma", "Rachid", "Bennani", "user", "mobile", False, comptes[2], [grp_oper]),
        ]
        users = []
        for email, prenom, nom, role, utype, is_staff, compte, groups in users_data:
            if not UserWeb.objects.filter(email=email).exists():
                u = UserWeb.objects.create_user(
                    email=email, role=role, password="Test@1234",
                    nom=nom, prenom=prenom, type=utype,
                    is_staff=is_staff, compte=compte,
                )
                u.groups.set(groups)
            else:
                u = UserWeb.objects.get(email=email)
            users.append(u)
        self.stdout.write(f"  Users: {len(users)}")

        admin_user = users[0]

        personnes_data = [
            ("Ahmed", "Bouazza", "M"), ("Nadia", "Lahlou", "F"),
            ("Hassan", "Chraibi", "M"), ("Salma", "Kettani", "F"),
            ("Driss", "Alaoui", "M"), ("Khadija", "Senhaji", "F"),
            ("Mourad", "Filali", "M"), ("Zineb", "Tahiri", "F"),
            ("Amine", "Benhima", "M"), ("Houda", "Squalli", "F"),
            ("Rachid", "Ouazzani", "M"), ("Imane", "Fassi Fihri", "F"),
            ("Karim", "Zemmouri", "M"), ("Meriem", "Benjelloun", "F"),
            ("Yassine", "Gharbaoui", "M"),
        ]
        personnes = []
        for prenom, nom, gender in personnes_data:
            obj, _ = Personne.objects.get_or_create(
                nom=nom, prenom=prenom,
                defaults={"gender": gender, "compte": compte_main},
            )
            personnes.append(obj)
        self.stdout.write(f"  Personnes: {len(personnes)}")

        cats_data = [
            "Informatique", "Mobilier", "Vehicules", "Equipement Industriel",
            "Telephonie", "Electromenager", "Securite", "Reseau",
        ]
        cats = []
        for lib in cats_data:
            obj, _ = categorie.objects.get_or_create(libelle=lib)
            cats.append(obj)
        self.stdout.write(f"  Categories: {len(cats)}")

        produits_data = [
            ("Ordinateur Portable", cats[0], 5, "individuellement"),
            ("Ecran Moniteur", cats[0], 5, "individuellement"),
            ("Imprimante", cats[0], 4, "individuellement"),
            ("Bureau", cats[1], 10, "individuellement"),
            ("Chaise Ergonomique", cats[1], 7, "individuellement"),
            ("Armoire de Rangement", cats[1], 10, "individuellement"),
            ("Voiture de Service", cats[2], 5, "individuellement"),
            ("Chariot Elevateur", cats[3], 8, "individuellement"),
            ("Smartphone", cats[4], 3, "individuellement"),
            ("Tablette", cats[4], 3, "individuellement"),
            ("Climatiseur", cats[5], 7, "individuellement"),
            ("Camera Surveillance", cats[6], 5, "individuellement"),
            ("Switch Reseau", cats[7], 5, "individuellement"),
            ("Fournitures Bureau", cats[1], 1, "en masse"),
            ("Cables Reseau", cats[7], 2, "en masse"),
        ]
        produits = []
        for lib, cat, duree, statut in produits_data:
            obj, _ = produit.objects.get_or_create(
                libelle=lib,
                defaults={"categorie": cat, "duree_amourtissement": duree, "statut": statut},
            )
            produits.append(obj)
        self.stdout.write(f"  Produits: {len(produits)}")

        natures_data = [
            "Immobilisation Corporelle", "Charge Consommable",
            "Bien Amortissable", "Stock Rotatif", "Equipement Technique",
        ]
        natures = []
        for lib in natures_data:
            obj, _ = nature.objects.get_or_create(libelle=lib)
            natures.append(obj)
        self.stdout.write(f"  Natures: {len(natures)}")

        fourns_data = [
            "Dell Maroc", "HP Afrique du Nord", "Ikea Casa",
            "Toyota Maroc", "Samsung Electronics MA", "Lenovo Distribution",
            "Steelcase Maghreb", "Cisco Systems MA", "Hyundai Maroc",
            "LG Electronics MA",
        ]
        fourns = []
        for nom in fourns_data:
            obj, _ = fournisseur.objects.get_or_create(
                nom=nom, defaults={"compte": compte_main},
            )
            fourns.append(obj)
        self.stdout.write(f"  Fournisseurs: {len(fourns)}")

        marques_data = [
            "Dell", "HP", "Lenovo", "Apple", "Samsung", "Toyota",
            "Ikea", "Steelcase", "Cisco", "LG", "Hyundai", "Epson",
        ]
        marques = []
        for nom in marques_data:
            obj, _ = marque.objects.get_or_create(nom=nom)
            marques.append(obj)
        self.stdout.write(f"  Marques: {len(marques)}")

        deps_data = [
            "Direction Generale", "Ressources Humaines", "Finance et Comptabilite",
            "Logistique", "IT et Systemes", "Commercial",
            "Production", "Qualite", "Maintenance",
        ]
        deps = []
        for nom in deps_data:
            obj, _ = departement.objects.get_or_create(
                nom=nom, defaults={"compte": compte_main},
            )
            deps.append(obj)
        self.stdout.write(f"  Departements: {len(deps)}")

        locs_data = [
            "Siege Casablanca", "Entrepot Ain Sebaa", "Bureau Rabat",
            "Depot Tanger", "Agence Marrakech",
        ]
        locs = []
        for nom in locs_data:
            obj, _ = location.objects.get_or_create(
                nom=nom, defaults={"compte": compte_main},
            )
            locs.append(obj)
        self.stdout.write(f"  Locations: {len(locs)}")

        zones_data = [
            ("Etage 1", locs[0]), ("Etage 2", locs[0]), ("Etage 3", locs[0]),
            ("Zone A - Stockage", locs[1]), ("Zone B - Expedition", locs[1]),
            ("Zone C - Reception", locs[1]),
            ("Bureau Principal", locs[2]), ("Salle de Reunion", locs[2]),
            ("Hall Principal", locs[3]), ("Zone Chargement", locs[3]),
            ("Showroom", locs[4]),
        ]
        zones = []
        for nom, loc in zones_data:
            obj, _ = zone.objects.get_or_create(
                nom=nom, defaults={"location": loc},
            )
            zones.append(obj)
        self.stdout.write(f"  Zones: {len(zones)}")

        emps_data = [
            ("Bureau DG-101", zones[0]), ("Bureau RH-102", zones[0]),
            ("Bureau Finance-103", zones[0]), ("Salle Serveur", zones[0]),
            ("Open Space IT", zones[1]), ("Bureau Commercial-201", zones[1]),
            ("Salle Formation", zones[1]), ("Bureau Direction-301", zones[2]),
            ("Salle Conference", zones[2]),
            ("Etagere A1", zones[3]), ("Etagere A2", zones[3]),
            ("Etagere A3", zones[3]), ("Rack B1", zones[4]),
            ("Rack B2", zones[4]), ("Quai Reception C1", zones[5]),
            ("Bureau Rabat-01", zones[6]), ("Salle Reunion Rabat", zones[7]),
            ("Entree Tanger", zones[8]), ("Quai Tanger", zones[9]),
            ("Vitrine Marrakech", zones[10]),
        ]
        emps = []
        for nom, z in emps_data:
            obj, _ = emplacement.objects.get_or_create(
                nom=nom, defaults={"zone": z},
            )
            emps.append(obj)
        self.stdout.write(f"  Emplacements: {len(emps)}")

        ttags_data = ["RFID UHF", "RFID HF", "Code Barre", "QR Code", "NFC"]
        ttags = []
        for nom in ttags_data:
            obj, _ = type_tag.objects.get_or_create(nom=nom)
            ttags.append(obj)
        self.stdout.write(f"  Types Tags: {len(ttags)}")

        tags = []
        for i in range(1, 61):
            ref = f"TAG-{i:06d}"
            obj, _ = tag.objects.get_or_create(
                reference=ref,
                defaults={
                    "statut": "on",
                    "affecter": False,
                    "type": random.choice(ttags),
                    "compte": compte_main,
                },
            )
            tags.append(obj)
        self.stdout.write(f"  Tags: {len(tags)}")

        tag_emps = []
        for i in range(1, 21):
            ref = f"4C4F43-EMP-{i:04d}"
            obj, _ = tagEmplacement.objects.get_or_create(
                reference=ref,
                defaults={
                    "statut": "on",
                    "affecter": False,
                    "type": random.choice(ttags),
                    "compte": compte_main,
                },
            )
            tag_emps.append(obj)
        self.stdout.write(f"  Tags Emplacements: {len(tag_emps)}")

        ops_data = [
            "Maintenance Preventive", "Reparation", "Mise a Niveau",
            "Remplacement Piece", "Calibration", "Nettoyage Industriel",
        ]
        ops = []
        for ref in ops_data:
            obj, _ = operation.objects.get_or_create(reference=ref)
            ops.append(obj)
        self.stdout.write(f"  Operations: {len(ops)}")

        fichiers_data = [
            ("import_articles_jan2024.xlsx", 45000, 120),
            ("import_articles_mar2024.xlsx", 32000, 85),
            ("import_articles_jul2024.xlsx", 67000, 200),
            ("import_mobilier_2025.xlsx", 28000, 60),
        ]
        fichiers = []
        for nom, taille, lignes in fichiers_data:
            obj, _ = Fichier.objects.get_or_create(
                nom=nom, defaults={"taille": taille, "nombre_lignes": lignes},
            )
            fichiers.append(obj)
        self.stdout.write(f"  Fichiers: {len(fichiers)}")

        articles_specs = [
            ("Dell Latitude 5540", 0, 0, 0, 0, 12500.00, 10, "FAC-2024-001"),
            ("Dell Latitude 7440", 0, 0, 0, 0, 18000.00, 5, "FAC-2024-002"),
            ("HP EliteBook 840 G10", 0, 1, 1, 0, 15000.00, 8, "FAC-2024-003"),
            ("Lenovo ThinkPad T14s", 0, 2, 5, 0, 14500.00, 6, "FAC-2024-004"),
            ("Dell UltraSharp U2723QE 27p", 1, 0, 0, 0, 6500.00, 15, "FAC-2024-005"),
            ("HP Z27k G3 4K", 1, 1, 1, 0, 7200.00, 10, "FAC-2024-006"),
            ("Epson EcoTank L6290", 2, 11, 0, 0, 3800.00, 4, "FAC-2024-007"),
            ("Bureau Executive 180cm", 3, 6, 2, 0, 4500.00, 12, "FAC-2024-008"),
            ("Bureau Standard 140cm", 3, 6, 2, 0, 2800.00, 20, "FAC-2024-009"),
            ("Chaise Herman Miller", 4, 7, 6, 0, 8500.00, 15, "FAC-2024-010"),
            ("Chaise Standard Bureau", 4, 6, 2, 0, 1500.00, 30, "FAC-2024-011"),
            ("Armoire Metallique 2P", 5, 6, 2, 0, 3200.00, 8, "FAC-2024-012"),
            ("Toyota Hilux 2024", 6, 5, 3, 2, 350000.00, 2, "FAC-2024-013"),
            ("Chariot Cat DP25N", 7, 10, 8, 4, 180000.00, 3, "FAC-2024-014"),
            ("Samsung Galaxy A54", 8, 4, 4, 0, 4200.00, 10, "FAC-2024-015"),
            ("Samsung Galaxy Tab S9", 9, 4, 4, 0, 6800.00, 5, "FAC-2024-016"),
            ("LG Climatiseur 12000BTU", 10, 9, 9, 4, 8500.00, 6, "FAC-2024-017"),
            ("Camera Hikvision DS-2CD", 11, 9, 9, 4, 2500.00, 12, "FAC-2024-018"),
            ("Cisco Catalyst 1000-24T", 12, 8, 7, 4, 12000.00, 4, "FAC-2025-001"),
            ("Lot Fournitures Q1-2025", 13, 6, 2, 1, 5000.00, 50, "FAC-2025-002"),
            ("Cables CAT6 (lot 100m)", 14, 8, 7, 1, 1200.00, 20, "FAC-2025-003"),
            ("HP LaserJet Pro M404dn", 2, 1, 1, 0, 4200.00, 3, "FAC-2025-004"),
            ("Apple MacBook Pro 14 M3", 0, 3, 0, 0, 25000.00, 3, "FAC-2025-005"),
        ]
        articles = []
        for desig, prod_i, marq_i, fourn_i, nat_i, prix, qte, facture in articles_specs:
            obj, created = article.objects.get_or_create(
                designation=desig,
                N_facture=facture,
                defaults={
                    "date_achat": rand_date(2023, 2025),
                    "prix_achat": prix,
                    "qte": qte,
                    "produit": produits[prod_i],
                    "marque": marques[marq_i],
                    "fournisseur": fourns[fourn_i],
                    "nature": natures[nat_i],
                    "compte": compte_main,
                    "fichier": random.choice(fichiers),
                },
            )
            articles.append(obj)
        self.stdout.write(f"  Articles: {len(articles)}")

        items = []
        tag_idx = 0
        for art in articles:
            count = min(art.qte or 1, 8)
            for j in range(count):
                emp = random.choice(emps[:15])
                dep = random.choice(deps)
                is_assigned = random.random() < 0.6
                personne = random.choice(personnes) if is_assigned else None
                statut_val = "affecter" if is_assigned else "non affecter"

                t = None
                if tag_idx < len(tags) and art.produit.statut == "individuellement":
                    t = tags[tag_idx]
                    t.affecter = True
                    t.save()
                    tag_idx += 1

                obj = item.objects.create(
                    article=art,
                    emplacement=emp,
                    departement=dep,
                    statut=statut_val,
                    affectation_personne=personne,
                    tag=t,
                    numero_serie=f"SN-{art.id:04d}-{j+1:03d}" if art.produit.statut == "individuellement" else None,
                )
                items.append(obj)
        self.stdout.write(f"  Items: {len(items)}")

        transfers = []
        for _ in range(30):
            it = random.choice(items)
            old_emp = random.choice(emps)
            new_emp = random.choice([e for e in emps if e != old_emp])
            old_dep = random.choice(deps)
            new_dep = random.choice([d for d in deps if d != old_dep])
            old_pers = random.choice(personnes)
            new_pers = random.choice([p for p in personnes if p != old_pers])
            obj = TransferHistorique.objects.create(
                item_transfer=it,
                old_emplacement=old_emp, new_emplacement=new_emp,
                old_departement=old_dep, new_departement=new_dep,
                old_personne=old_pers, new_personne=new_pers,
            )
            transfers.append(obj)
        self.stdout.write(f"  Transfers: {len(transfers)}")

        op_articles = []
        for _ in range(20):
            it = random.choice(items)
            op = random.choice(ops)
            obj = operation_article.objects.create(
                item=it,
                operation=op,
                prix=round(random.uniform(200, 15000), 2),
                date_operation=rand_date(2024, 2026),
                commentaire=random.choice([
                    "Remplacement du disque SSD",
                    "Nettoyage complet et verification",
                    "Mise a jour firmware",
                    "Reparation ecran",
                    "Changement batterie",
                    "Calibration capteurs",
                    "Revision annuelle",
                    "Remplacement clavier",
                ]),
            )
            op_articles.append(obj)
        self.stdout.write(f"  Operation Articles: {len(op_articles)}")

        inv_data = [
            ("Inventaire Annuel 2024", "Location", None, "Terminer"),
            ("Inventaire Q1 2025 - Siege", "Zone", None, "Terminer"),
            ("Inventaire IT Mars 2025", "Departement", deps[4], "En cours"),
            ("Inventaire Entrepot Ain Sebaa", "Location", None, "En cours"),
            ("Inventaire Mobilier 2025", "Emplacement", None, "En attente"),
        ]
        invs = []
        for nom, cat, dep, statut in inv_data:
            obj = inventaire.objects.create(
                nom=nom,
                categorie=cat,
                user=admin_user,
                statut=statut,
                departement=dep,
                date_creation=rand_dt(2024, 2026),
                date_debut=rand_dt(2024, 2026) if statut != "En attente" else None,
                date_fin=rand_dt(2025, 2026) if statut == "Terminer" else None,
            )
            invs.append(obj)
        self.stdout.write(f"  Inventaires: {len(invs)}")

        inv_emps = []
        for inv in invs:
            sample_emps = random.sample(emps, min(6, len(emps)))
            for emp in sample_emps:
                if inv.statut == "Terminer":
                    st = "Terminer"
                elif inv.statut == "En cours":
                    st = random.choice(["Terminer", "En cours", "en attente"])
                else:
                    st = "en attente"
                obj = inventaire_emplacement.objects.create(
                    emplacement=emp,
                    inventaire=inv,
                    statut=st,
                    affceted_at=random.choice(users[:5]),
                    start_at=(st != "en attente"),
                )
                inv_emps.append(obj)
        self.stdout.write(f"  Inventaire Emplacements: {len(inv_emps)}")

        details = []
        for inv_emp in inv_emps:
            sample_items = random.sample(items, min(4, len(items)))
            for it in sample_items:
                etat = random.choice(["Trouve", "Manquant", "Endommage", "Deplace"])
                obj = detail_inventaire.objects.create(
                    inventaire_emplacement=inv_emp,
                    item=it,
                    etat=etat,
                )
                details.append(obj)
        self.stdout.write(f"  Details Inventaire: {len(details)}")

        archived = random.sample(items, min(10, len(items)))
        archive_objs = []
        comments = [
            "Hors service - carte mere defaillante",
            "Obsolete - remplacement prevu",
            "Endommage suite a chute",
            "Fin de vie - amortissement complet",
            "Retour fournisseur - defaut fabrication",
            "Desaffecte suite a reorganisation",
            "Panne irreparable",
            "Mis au rebut",
            "Don a association",
            "Vol declare",
        ]
        for i, it in enumerate(archived):
            it.archive = True
            it.date_archive = rand_date(2024, 2026)
            it.save()
            obj = ArchiveItem.objects.create(
                item_archive=it,
                commentaire=comments[i % len(comments)],
            )
            archive_objs.append(obj)
        self.stdout.write(f"  Archives: {len(archive_objs)}")

        tag_histories = []
        tagged_items = [it for it in items if it.tag is not None]
        for i in range(min(15, len(tagged_items))):
            it = tagged_items[i]
            old_t = random.choice(tags)
            new_t = it.tag
            obj = TagHistory.objects.create(
                item=it,
                old_tag=old_t if old_t != new_t else None,
                new_tag=new_t,
                changed_by=random.choice(users[:5]),
            )
            tag_histories.append(obj)
        self.stdout.write(f"  Tag Histories: {len(tag_histories)}")

        tag_emp_histories = []
        for i in range(min(8, len(tag_emps))):
            emp = emps[i]
            obj = TagHistoryEmplacement.objects.create(
                emplacement=emp,
                old_tag=None,
                new_tag=tag_emps[i],
                changed_by=random.choice(users[:5]),
            )
            tag_emp_histories.append(obj)
        self.stdout.write(f"  Tag Emp Histories: {len(tag_emp_histories)}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS("  AMS Database Seeded Successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(f"  Comptes:              {Compte.objects.count()}")
        self.stdout.write(f"  Users:                {UserWeb.objects.count()}")
        self.stdout.write(f"  Personnes:            {Personne.objects.count()}")
        self.stdout.write(f"  Categories:           {categorie.objects.count()}")
        self.stdout.write(f"  Produits (Familles):  {produit.objects.count()}")
        self.stdout.write(f"  Natures:              {nature.objects.count()}")
        self.stdout.write(f"  Fournisseurs:         {fournisseur.objects.count()}")
        self.stdout.write(f"  Marques:              {marque.objects.count()}")
        self.stdout.write(f"  Departements:         {departement.objects.count()}")
        self.stdout.write(f"  Locations:            {location.objects.count()}")
        self.stdout.write(f"  Zones:                {zone.objects.count()}")
        self.stdout.write(f"  Emplacements:         {emplacement.objects.count()}")
        self.stdout.write(f"  Types Tags:           {type_tag.objects.count()}")
        self.stdout.write(f"  Tags:                 {tag.objects.count()}")
        self.stdout.write(f"  Tags Emplacements:    {tagEmplacement.objects.count()}")
        self.stdout.write(f"  Operations:           {operation.objects.count()}")
        self.stdout.write(f"  Fichiers:             {Fichier.objects.count()}")
        self.stdout.write(f"  Articles:             {article.objects.count()}")
        self.stdout.write(f"  Items:                {item.objects.count()}")
        self.stdout.write(f"  Transfers:            {TransferHistorique.objects.count()}")
        self.stdout.write(f"  Operation Articles:   {operation_article.objects.count()}")
        self.stdout.write(f"  Inventaires:          {inventaire.objects.count()}")
        self.stdout.write(f"  Inv. Emplacements:    {inventaire_emplacement.objects.count()}")
        self.stdout.write(f"  Details Inventaire:   {detail_inventaire.objects.count()}")
        self.stdout.write(f"  Archives:             {ArchiveItem.objects.count()}")
        self.stdout.write(f"  Tag Histories:        {TagHistory.objects.count()}")
        self.stdout.write(f"  Tag Emp Histories:    {TagHistoryEmplacement.objects.count()}")
PYEOF

echo "Running seed_data..."
cd /opt/DevOPS/AMS-V2
docker compose exec web python manage.py seed_data
