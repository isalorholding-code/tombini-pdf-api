from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os, tempfile, requests, uuid

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

app = FastAPI(title="Tombini PDF Generator", version="3.0.0")

SUPABASE_URL    = os.environ.get("SUPABASE_URL", "https://bdtqjnljceskevsuqyln.supabase.co")
SUPABASE_KEY    = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = "pdfs"

DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_TOMBINI = os.path.join(DIR, 'logo_grupo_tombini.jpg')
LOGO_SMOKE   = os.path.join(DIR, 'logo_smokecheck.jpg')

class DadosEnsaio(BaseModel):
    placa: str
    marca: str
    modelo: str
    fabricacao: str
    km_atual: str
    data_ensaio: str
    validade: str
    lim_marcha_lenta: Optional[str] = "450 - 750"
    lim_rotacao_corte: Optional[str] = "2350 - 2450"
    lim_opacidade: Optional[str] = "1,08"
    lim_ruido: Optional[str] = "89"
    ensaio_1: str
    ensaio_2: str
    ensaio_3: str
    ensaio_4: str
    media_opacidade: str
    resultado: str
    responsavel: Optional[str] = "001 - Samantha B. P. Pinez"
    opacimetro_modelo: Optional[str] = "Smoke Check 2000"
    opacimetro_serial: Optional[str] = "53.558"
    opacimetro_valido_ate: Optional[str] = "07/11/2025"
    software_versao: Optional[str] = "4.0.4"

def S(name, size=9, bold=False, align=TA_LEFT, color=colors.black, leading=None):
    kwargs = dict(fontSize=size, fontName='Helvetica-Bold' if bold else 'Helvetica', textColor=color, alignment=align)
    if leading: kwargs['leading'] = leading
    return ParagraphStyle(name, **kwargs)

def P(txt, size=9, bold=False, align=TA_LEFT):
    return Paragraph(str(txt), S(f'_p{abs(hash(str(txt)+str(size)+str(bold)))}', size=size, bold=bold, align=align))

TS_PLAIN = TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),('VALIGN',(0,0),(-1,-1),'TOP')])

def secao(titulo, W, extra=''):
    texto = f'<b>{titulo}</b>'
    if extra: texto += f'&nbsp;&nbsp;&nbsp;&nbsp;{extra}'
    return [Paragraph(texto, S('sh', size=10)), HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=3)]

def gerar_pdf(d, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=10*mm, bottomMargin=10*mm)
    story = []
    W = 174*mm
    if os.path.exists(LOGO_TOMBINI):
        logo = Image(LOGO_TOMBINI, width=45*mm, height=16*mm)
        logo.hAlign = 'CENTER'
        story.append(logo)
        story.append(Spacer(1, 2*mm))
    for txt in ['Tombini &amp; Cia. LTDA, CNPJ/CPF: 82.809.088/0006-66','Endereco: Rua Antonio Ovidio Rodrigues 693, Setor Industrial III','Fone: (11) 45252575 - diego.blanger@grupotombini.com.br']:
        story.append(Paragraph(txt, S('hdr', size=8, align=TA_CENTER)))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph('<b>Ensaio Armazenado Opacimetro 28</b>', S('titulo', size=11, align=TA_CENTER)))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=4))
    story.append(Spacer(1, 2*mm))
    story += secao('Dados do Veiculo', W)
    story.append(Spacer(1, 2*mm))
    vdata = [
        [P('Marca:'), P(d['marca']), P('Limite Marcha Lenta:'), P(d.get('lim_marcha_lenta','450 - 750'), align=TA_RIGHT)],
        [P('Modelo:'), P(d['modelo']), P('Limite Rotacao Corte:'), P(d.get('lim_rotacao_corte','2350 - 2450'), align=TA_RIGHT)],
        [P('Tipo Motor:'), P(''), P('Limite Opacidade:'), P(d.get('lim_opacidade','1,08'), align=TA_RIGHT)],
        [Paragraph(f"Placa: <b>{d['placa']}</b>   Km Atual: {d['km_atual']}   Fabricacao: {d['fabricacao']}", S('pl', size=9)), '', P('Limite Ruido:'), P(d.get('lim_ruido','89'), align=TA_RIGHT)],
    ]
    tv = Table(vdata, colWidths=[20*mm, 72*mm, 52*mm, 30*mm])
    tv.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),2),('SPAN',(0,3),(1,3)),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,-1),(-1,-1),0.5,colors.HexColor('#AAAAAA'))]))
    story.append(tv)
    story.append(Spacer(1, 3*mm))
    story += secao('Dados do Cliente', W)
    story.append(Spacer(1, 2*mm))
    for txt in ['Grupo Tombini - CNPJ/CPF: 82.809.088/0006-66','Endereco: R: Antonio Ovidio Rodrigues 693 - JUNDIAI - SAO PAULO','Fone: (11)45257525, eng.trabalho@grupotombini.com.br']:
        story.append(Paragraph(txt, S('cli', size=9, align=TA_CENTER)))
    story.append(Spacer(1, 3*mm))
    story += secao('Dados do Ensaio', W, extra=f'Inicio: {d["data_ensaio"]}')
    story.append(Spacer(1, 2*mm))
    t_e1 = Table([[Paragraph('<b>Ruido Aferido:</b>  0,00', S('e1')), Paragraph('<b>Altitude:</b>  Acima de 350m', S('e2', align=TA_CENTER)), Paragraph('<b>Temperatura Aferida:</b>  0,00C', S('e3', align=TA_RIGHT))]], colWidths=[55*mm, 65*mm, 54*mm])
    t_e1.setStyle(TS_PLAIN)
    story.append(t_e1)
    story.append(Paragraph('Temperatura fornecida visualmente', S('tv', align=TA_CENTER)))
    story.append(Spacer(1, 1*mm))
    t_e2 = Table([[Paragraph('RPM Marcha Lenta Tolerada: 350 - 850', S('rpmml')), Paragraph('Rotacao de Corte Tolerada: 2150 - 2550', S('rpmc'))]], colWidths=[90*mm, 84*mm])
    t_e2.setStyle(TS_PLAIN)
    story.append(t_e2)
    story.append(Spacer(1, 3*mm))
    TACC_W = 80*mm
    hs = S('th', size=9, bold=True, align=TA_CENTER)
    vs = S('tv2', size=9, bold=True, align=TA_CENTER)
    acc_data = [[Paragraph('<b>Aceleracao</b>', hs), Paragraph('<b>Opacidade K(m<super>-1</super>)</b>', hs)]]
    for i, v in enumerate([d['ensaio_1'], d['ensaio_2'], d['ensaio_3'], d['ensaio_4']], 1):
        acc_data.append([Paragraph(str(i), vs), Paragraph(str(v), vs)])
    t_acc = Table(acc_data, colWidths=[TACC_W/2, TACC_W/2])
    t_acc.setStyle(TableStyle([('BOX',(0,0),(-1,-1),1,colors.black),('INNERGRID',(0,0),(-1,-1),0.5,colors.black),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('ALIGN',(0,0),(-1,-1),'CENTER')]))
    outer = Table([[t_acc]], colWidths=[W])
    outer.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(outer)
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    cor_res = colors.HexColor('#1E8449') if d['resultado'] == 'APROVADO' else colors.HexColor('#C0392B')
    t_res = Table([[Paragraph('<b>Resultado do Veiculo</b>', S('rvl', size=10)), Paragraph(f'<b>{d["placa"]}</b>', S('rvp', size=10)), Paragraph(f'<b>Media: {d["media_opacidade"]}</b>', S('rvm', size=10)), Paragraph(f'<b>{d["resultado"]}</b>', S('rvr', size=11, color=cor_res))]], colWidths=[48*mm, 30*mm, 40*mm, 56*mm])
    t_res.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),2),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(t_res)
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    story.append(Spacer(1, 4*mm))
    t_dt = Table([[Paragraph(f'<b>{d["data_ensaio"]}</b>', S('dtv', align=TA_CENTER)), Paragraph(f'<b>{d["validade"]}</b>', S('vdv', align=TA_CENTER)), Paragraph(f'Responsavel: {d.get("responsavel","001 - Samantha B. P. Pinez")}', S('resp'))],[Paragraph('Data do Ensaio', S('dtl', size=8, align=TA_CENTER)), Paragraph('Validade', S('vdl', size=8, align=TA_CENTER)), '']], colWidths=[42*mm, 42*mm, 90*mm])
    t_dt.setStyle(TableStyle([('LINEABOVE',(0,0),(1,0),0.8,colors.black),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),('LEFTPADDING',(0,0),(-1,-1),2),('ALIGN',(0,0),(1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story.append(t_dt)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('Observacao:', S('obs')))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#AAAAAA'), spaceAfter=2))
    story.append(Spacer(1, 8*mm))
    story += secao('Dados do Opacimetro/Software', W)
    story.append(Spacer(1, 2*mm))
    textos_opc = [f'Opacimetro Modelo: {d.get("opacimetro_modelo","Smoke Check 2000")}   Serial: {d.get("opacimetro_serial","53.558")}   Valido ate: {d.get("opacimetro_valido_ate","07/11/2025")}','Tacometro  Serial:','Fabricante: Altanova Industrial e Comercial EIRELI EPP.',f'Software Syscon Versao {d.get("software_versao","4.0.4")}']
    col_txt = [[Paragraph(t, S(f'opc{i}', size=9))] for i, t in enumerate(textos_opc)]
    if os.path.exists(LOGO_SMOKE):
        logo_smoke = Image(LOGO_SMOKE, width=35*mm, height=12*mm)
        t_opc = Table([[col_txt, logo_smoke]], colWidths=[130*mm, 44*mm])
    else:
        t_opc = Table([[col_txt]], colWidths=[W])
    t_opc.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story.append(t_opc)
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('Pag. 1 de 1', S('rod', size=8, align=TA_RIGHT, color=colors.grey)))
    doc.build(story)

def upload_supabase(filepath, filename):
    with open(filepath, 'rb') as f:
        conteudo = f.read()
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    headers = {"Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/pdf", "x-upsert": "true"}
    resp = requests.post(url, headers=headers, data=conteudo)
    if resp.status_code not in (200, 201):
        raise Exception(f"Erro upload Supabase: {resp.status_code} - {resp.text}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"

@app.get("/")
def root():
    return {"status": "ok", "msg": "Tombini PDF API v3 - POST /gerar-pdf"}

@app.post("/gerar-pdf")
def gerar_pdf_endpoint(dados: DadosEnsaio):
    try:
        uid = str(uuid.uuid4())[:8]
        filename = f"{dados.placa}_{uid}.pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        gerar_pdf(dados.dict(), tmp.name)
        url_pdf = upload_supabase(tmp.name, filename)
        os.unlink(tmp.name)
        return JSONResponse(content={"success": True, "url": url_pdf, "placa": dados.placa, "filename": filename})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
