"""access_app/report.py — informe descriptivo generado únicamente con ensayos aportados."""
from html import escape


def render_report(report):
    def fraction(metric):
        if not metric["total"]:
            return "Sin datos (denominador 0)"
        return f'{metric["count"]} / {metric["total"]} ({metric["rate"]*100:.1f} %)'
    blocks = []
    for session in report["sessions"]:
        rows = []
        for label, key in (("Inscritos correctos", "known_correct"), ("Inscritos rechazados", "known_rejected"),
                           ("Identidad equivocada", "known_wrong_identity"), ("No inscritos aceptados", "unknown_accepted"),
                           ("Capturas no aptas", "capture_not_suitable")):
            rows.append("<tr><td>"+label+"</td><td>"+fraction(session["model"][key])+"</td><td>"+
                        fraction(session["baseline_nearest_without_rejection"][key])+"</td></tr>")
        conditions = "".join("<li>"+escape(condition)+": no inscritos aceptados "+fraction(value["unknown_accepted"])+
                             "; inscritos correctos "+fraction(value["known_correct"])+"</li>"
                             for condition, value in session["by_condition"].items())
        blocks.append("<section><h2>"+escape(session["session"])+" · "+escape(session["phase"])+"</h2><p>"+
            str(session["trials"])+" ensayos; "+str(session["participants"])+" códigos de participante; padrón de "+
            str(session["configuration"]["gallery_size"])+" personas.</p><table><thead><tr><th>Métrica</th>"
            "<th>Sistema con rechazo</th><th>Línea base sin rechazo</th></tr></thead><tbody>"+"".join(rows)+
            "</tbody></table><p>Procesamiento mediana / p95: "+f'{session["latency_processing_ms_median"]:.1f} / '+
            f'{session["latency_processing_ms_p95"]:.1f} ms'+". No incluye cámara, red ni pantalla.</p><h3>Condiciones</h3><ul>"+
            conditions+"</ul><p>Configuración: umbral "+str(session["configuration"]["threshold"])+", margen "+
            str(session["configuration"]["margin"])+". Huella: <code>"+escape(session["configuration_id"])+"</code>.</p></section>")
    limitations = "".join("<li>"+escape(text)+"</li>" for text in report["limitations"])
    return '<!doctype html><html lang="es"><meta charset="utf-8"><title>Evaluación · Acceso Residencial</title>'+\
        '<style>body{font:16px/1.6 Segoe UI,Arial,sans-serif;color:#183538;max-width:1040px;margin:45px auto;padding:20px}h1,h2{color:#096b60}section{margin:40px 0;border-top:1px solid #ccc}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd8d4;padding:10px;text-align:left}th{background:#e9f3ef}code{overflow-wrap:anywhere;font-size:12px}.notice{padding:16px;background:#fff4d8}@media print{body{margin:0}section{break-inside:avoid}}</style>'+\
        '<h1>Evaluación del reconocimiento facial</h1><p class="notice">Informe descriptivo de capturas voluntarias etiquetadas. '+\
        'No certifica seguridad, identidad, apertura física ni ausencia de sesgos. Los resultados no sustituyen el informe académico final.</p>'+\
        ('<p>No hay ensayos aportados. No se calculó precisión.</p>' if not blocks else ''.join(blocks))+\
        '<h2>Interpretación y límites</h2><ul>'+limitations+'</ul><p>La línea base comparte detector, control de calidad y descriptor; cambia la regla de rechazo. '+\
        'Escenas vacías/múltiples no inflan denominadores de identidad. Las sesiones y códigos no prueban independencia. '+\
        'No ajustar parámetros con una prueba declarada reservada. Cero errores observados no implica error real cero.</p></html>'
