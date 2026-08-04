"""
app.py - Tableau de bord KPI du pipeline FactCheck (livrable 5).

Lancement :
    streamlit run 05_dashboard/app.py

Affiche trois familles de KPI, pensées pour un public non technique :
- PRÉCISION des données (qualité)
- RAPIDITÉ (durée des étapes)
- COÛT / volume

Toute la logique de calcul est dans metrics.py ; ce fichier ne fait que l'affichage.
"""
import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import (
    load_dataset, compute_data_kpis, run_timed_pipeline, load_run_metrics,
)

st.set_page_config(page_title="CheckIt.AI — KPI du pipeline", page_icon="📊", layout="wide")

st.title("📊 CheckIt.AI — Tableau de bord du pipeline")
st.caption("Qualité, rapidité et volume des données multimodales extraites pour le détecteur de fake news.")

df = load_dataset()

if df is None:
    st.warning("Aucun dataset trouvé dans `data/processed/`. "
               "Lance d'abord le pipeline (extraction + transformation) ci-dessous.")
    if st.button("▶️ Lancer un run du pipeline"):
        with st.spinner("Extraction + transformation en cours..."):
            run_timed_pipeline()
        st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# 1. KPI de précision / qualité
# ---------------------------------------------------------------------------
kpis = compute_data_kpis(df)
st.subheader("Précision des données")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Publications", kpis["total"])
c2.metric("Multimodales", f"{kpis['pct_multimodal']} %", help="Texte ET image exploitables")
c3.metric("Sources fiables", f"{kpis['pct_trusted']} %", help="Domaine dans la liste de confiance")
c4.metric("Avec image", f"{kpis['pct_with_image']} %")

c5, c6, c7 = st.columns(3)
c5.metric("Longueur texte moy.", f"{int(kpis['avg_text_length'])} car.")
c6.metric("Domaines distincts", kpis["n_domains"])
c7.metric("Langues", kpis["n_languages"])

# ---------------------------------------------------------------------------
# 2. Répartitions (graphiques)
# ---------------------------------------------------------------------------
st.subheader("Répartitions")
g1, g2 = st.columns(2)

with g1:
    trust = df["source_trust"].value_counts().reset_index()
    trust.columns = ["source_trust", "count"]
    fig = px.pie(trust, names="source_trust", values="count",
                 title="Fiabilité des sources", hole=0.4,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig, use_container_width=True)

with g2:
    quality = df["image_quality"].value_counts().reset_index()
    quality.columns = ["image_quality", "count"]
    fig = px.bar(quality, x="image_quality", y="count",
                 title="Qualité des images", text="count",
                 color_discrete_sequence=["#4C78A8"])
    st.plotly_chart(fig, use_container_width=True)

g3, g4 = st.columns(2)

with g3:
    top = df["domain"].value_counts().head(10).reset_index()
    top.columns = ["domain", "count"]
    fig = px.bar(top, x="count", y="domain", orientation="h",
                 title="Top 10 domaines", text="count",
                 color_discrete_sequence=["#72B7B2"])
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with g4:
    if "published_date" in df.columns and df["published_date"].notna().any():
        timeline = df["published_date"].value_counts().sort_index().reset_index()
        timeline.columns = ["published_date", "count"]
        fig = px.line(timeline, x="published_date", y="count", markers=True,
                      title="Publications par date")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de dates exploitables pour la frise temporelle.")

# ---------------------------------------------------------------------------
# 3. KPI de rapidité / coût
# ---------------------------------------------------------------------------
st.subheader("Rapidité & coût du pipeline")
run = load_run_metrics()

if run is None:
    st.info("Aucune mesure de temps enregistrée. Lance un run chronométré pour les obtenir.")
else:
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Extraction", f"{run.get('extract_s', 0)} s")
    t2.metric("Transformation", f"{run.get('transform_s', 0)} s")
    t3.metric("Total", f"{run.get('total_s', 0)} s")
    t4.metric("Lignes produites", run.get("rows", 0))

    stages = {"extract": run.get("extract_s", 0), "transform": run.get("transform_s", 0)}
    fig = px.bar(x=list(stages.keys()), y=list(stages.values()),
                 labels={"x": "étape", "y": "secondes"},
                 title="Durée par étape", text=list(stages.values()),
                 color_discrete_sequence=["#E45756"])
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Coût / volume : {run.get('rows', 0)} lignes — "
               f"CSV {run.get('csv_kb', 0)} Ko, Parquet {run.get('parquet_kb', 0)} Ko. "
               f"Dernier run : {run.get('ran_at', 'n/a')}")

if st.button("🔄 Relancer un run chronométré"):
    with st.spinner("Run en cours..."):
        run_timed_pipeline()
    st.rerun()

# ---------------------------------------------------------------------------
# Aperçu des données
# ---------------------------------------------------------------------------
with st.expander("Aperçu des données (10 lignes)"):
    st.dataframe(
        df[["domain", "source_trust", "is_multimodal", "image_quality",
            "published_date", "text_length_clean", "title_clean"]].head(10),
        use_container_width=True,
    )
