import xml.etree.ElementTree as ET
import urllib.parse
from uuid import uuid4

def create_base_mxfile():
    root = ET.Element("mxfile", host="Electron", modified="2023-10-25T00:00:00.000Z", agent="Mozilla/5.0", version="22.0.4", type="device")
    diagram = ET.SubElement(root, "diagram", id=uuid4().hex[:8], name="Page-1")
    graph_model = ET.SubElement(diagram, "mxGraphModel", dx="1000", dy="1000", grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth="850", pageHeight="1100", math="0", shadow="0")
    root_node = ET.SubElement(graph_model, "root")
    ET.SubElement(root_node, "mxCell", id="0")
    ET.SubElement(root_node, "mxCell", id="1", parent="0")
    return root, root_node

def add_lifeline(root_node, id, name, x, y=40, width=100, height=500):
    cell = ET.SubElement(root_node, "mxCell", id=id, value=name, style="shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;outlineConnect=0;", vertex="1", parent="1")
    ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(width), height=str(height), **{"as": "geometry"})

def add_message(root_node, id, name, source, target, y, is_dashed=False):
    style = "html=1;verticalAlign=bottom;endArrow=block;edgeStyle=elbowEdgeStyle;elbow=vertical;curved=0;rounded=0;"
    if is_dashed:
        style += "dashed=1;endArrow=open;"
    
    cell = ET.SubElement(root_node, "mxCell", id=id, value=name, style=style, edge="1", parent="1", source=source, target=target)
    geometry = ET.SubElement(cell, "mxGeometry", width="80", relative="1", **{"as": "geometry"})
    # Array mapping
    points = ET.SubElement(geometry, "Array", **{"as": "points"})
    # Need to give coordinate hints
    ET.SubElement(points, "mxPoint", x="0", y=str(y))

# 2. Crawler Sequence
r, rn = create_base_mxfile()
add_lifeline(rn, "c_admin", "Admin/CRON", 100, 40, 100, 500)
add_lifeline(rn, "c_crawl", "Crawler", 250, 40, 100, 500)
add_lifeline(rn, "c_web", "Sources Web", 400, 40, 100, 500)
add_lifeline(rn, "c_nlp", "Modèle NLP", 550, 40, 100, 500)
add_lifeline(rn, "c_gdb", "Vector DB", 700, 40, 100, 500)

add_message(rn, "m1", "Déclenche collecte", "c_admin", "c_crawl", 100)
add_message(rn, "m2", "Requête articles", "c_crawl", "c_web", 150)
add_message(rn, "m3", "Retourne HTML", "c_web", "c_crawl", 200, True)
add_message(rn, "m4", "Envoi txt pour Vector", "c_crawl", "c_nlp", 250)
add_message(rn, "m5", "Retourne Vecteurs", "c_nlp", "c_crawl", 300, True)
add_message(rn, "m6", "Sauvegarde Txt+Vecteurs", "c_crawl", "c_gdb", 350)
add_message(rn, "m7", "Succès", "c_gdb", "c_crawl", 400, True)
add_message(rn, "m8", "Fin", "c_crawl", "c_admin", 450, True)
with open("/home/rooney/Desktop/PROJECT_PERSO/rdc-news-intelligence/ai-service/docs/Diagramme_Sequence_Crawler.drawio", "wb") as f:
    f.write(ET.tostring(r, encoding="utf-8"))

# 3. Interception Sequence
r, rn = create_base_mxfile()
add_lifeline(rn, "i_user", "Utilisateur", 100, 40, 100, 500)
add_lifeline(rn, "i_wb", "Webhook", 250, 40, 100, 500)
add_lifeline(rn, "i_ocr", "Vision/OCR", 400, 40, 100, 500)
add_lifeline(rn, "i_cls", "Classification", 550, 40, 100, 500)

add_message(rn, "im1", "Envoie texte/image", "i_user", "i_wb", 100)
add_message(rn, "im2", "Evac image (OCR)", "i_wb", "i_ocr", 150)
add_message(rn, "im3", "Texte extrait", "i_ocr", "i_wb", 200, True)
add_message(rn, "im4", "Eval. Thème", "i_wb", "i_cls", 250)
add_message(rn, "im5", "Theme (Polit/Santé/Sport)", "i_cls", "i_wb", 300, True)
add_message(rn, "im6", "Déclenche Vérif", "i_wb", "i_wb", 350)
with open("/home/rooney/Desktop/PROJECT_PERSO/rdc-news-intelligence/ai-service/docs/Diagramme_Sequence_Interception.drawio", "wb") as f:
    f.write(ET.tostring(r, encoding="utf-8"))

# 4. RAG / Verification Sequence
r, rn = create_base_mxfile()
add_lifeline(rn, "r_wb", "Orchestrateur RAG", 100, 40, 150, 500)
add_lifeline(rn, "r_vdb", "Vector DB", 300, 40, 100, 500)
add_lifeline(rn, "r_llm", "Service LLM", 450, 40, 100, 500)
add_lifeline(rn, "r_usr", "Groupe/Utilisateur", 600, 40, 150, 500)

add_message(rn, "rm1", "Req similarité", "r_wb", "r_vdb", 100)
add_message(rn, "rm2", "Retourne Docs+Sources", "r_vdb", "r_wb", 150, True)
add_message(rn, "rm3", "Générer réponse RAG", "r_wb", "r_llm", 200)
add_message(rn, "rm4", "Résumé + Verdict", "r_llm", "r_wb", 250, True)
add_message(rn, "rm5", "Formate Message", "r_wb", "r_wb", 300)
add_message(rn, "rm6", "Répond avec vérif+Sources", "r_wb", "r_usr", 350)
with open("/home/rooney/Desktop/PROJECT_PERSO/rdc-news-intelligence/ai-service/docs/Diagramme_Sequence_Verification.drawio", "wb") as f:
    f.write(ET.tostring(r, encoding="utf-8"))

# 5. General Sequence End-to-End
r, rn = create_base_mxfile()
add_lifeline(rn, "g_usr", "Utilisateur WP/TG", 80, 40, 120, 550)
add_lifeline(rn, "g_wb", "Webhook Core", 220, 40, 120, 550)
add_lifeline(rn, "g_cls", "Classification", 360, 40, 120, 550)
add_lifeline(rn, "g_vdb", "Vector Database", 500, 40, 120, 550)
add_lifeline(rn, "g_rag", "LLM RAG Gen", 640, 40, 120, 550)

add_message(rn, "gm1", "Message Info", "g_usr", "g_wb", 100)
add_message(rn, "gm2", "Analyse Intent/Thème", "g_wb", "g_cls", 150)
add_message(rn, "gm3", "Pol/San/Spo", "g_cls", "g_wb", 200, True)
add_message(rn, "gm4", "Cherche Faits (Sémantique)", "g_wb", "g_vdb", 250)
add_message(rn, "gm5", "Retourne Contexte", "g_vdb", "g_wb", 300, True)
add_message(rn, "gm6", "Demande génération RAG", "g_wb", "g_rag", 350)
add_message(rn, "gm7", "Génère Résumé+Sources", "g_rag", "g_wb", 400, True)
add_message(rn, "gm8", "Publie Verdict", "g_wb", "g_usr", 450)
with open("/home/rooney/Desktop/PROJECT_PERSO/rdc-news-intelligence/ai-service/docs/Diagramme_Sequence_Generale.drawio", "wb") as f:
    f.write(ET.tostring(r, encoding="utf-8"))

# 1. Use Case Diagram
r, rn = create_base_mxfile()
# Actors
ET.SubElement(rn, "mxCell", id="a1", value="Utilisateur", style="shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;", vertex="1", parent="1").append(ET.Element("mxGeometry", x="50", y="200", width="30", height="60", **{"as": "geometry"}))
ET.SubElement(rn, "mxCell", id="a2", value="Admin/CRON", style="shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;", vertex="1", parent="1").append(ET.Element("mxGeometry", x="50", y="400", width="30", height="60", **{"as": "geometry"}))
ET.SubElement(rn, "mxCell", id="a3", value="Sources Web", style="shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;", vertex="1", parent="1").append(ET.Element("mxGeometry", x="700", y="400", width="30", height="60", **{"as": "geometry"}))
# System Boundary
ET.SubElement(rn, "mxCell", id="sys", value="Système de Vérification (RDC News)", style="swimlane;whiteSpace=wrap;html=1;", vertex="1", parent="1").append(ET.Element("mxGeometry", x="150", y="50", width="450", height="550", **{"as": "geometry"}))
# Use cases
y_start = 100
for i, name in enumerate(["Envoyer un message (Txt/Img)", "Intercepter & Analyser", "Classifier (Polit,Santé,Sport)", "Vérifier l'information", "Générer un résumé RAG", "Répondre (Sources/Verdict)", "Crawler informations", "Vectoriser les données", "Mettre à jour Connaissance"]):
    ET.SubElement(rn, "mxCell", id=f"uc{i+1}", value=name, style="ellipse;whiteSpace=wrap;html=1;", vertex="1", parent="sys").append(ET.Element("mxGeometry", x="125", y=str(y_start + i*50), width="200", height="40", **{"as": "geometry"}))

# Connect actors to UC
ET.SubElement(rn, "mxCell", id="e1", style="endArrow=none;html=1;", edge="1", parent="1", source="a1", target="uc1").append(ET.Element("mxGeometry", **{"as": "geometry"}))
ET.SubElement(rn, "mxCell", id="e2", style="endArrow=none;html=1;", edge="1", parent="1", source="uc6", target="a1").append(ET.Element("mxGeometry", **{"as": "geometry"}))
ET.SubElement(rn, "mxCell", id="e3", style="endArrow=none;html=1;", edge="1", parent="1", source="a2", target="uc7").append(ET.Element("mxGeometry", **{"as": "geometry"}))
ET.SubElement(rn, "mxCell", id="e4", style="endArrow=none;html=1;", edge="1", parent="1", source="uc7", target="a3").append(ET.Element("mxGeometry", **{"as": "geometry"}))
with open("/home/rooney/Desktop/PROJECT_PERSO/rdc-news-intelligence/ai-service/docs/Diagramme_Cas_Utilisation.drawio", "wb") as f:
    f.write(ET.tostring(r, encoding="utf-8"))

print("Created 5 drawio files.")
