from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os, tempfile, requests, uuid, base64, io

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

# ─── Autenticação por API Key ────────────────────────────────────────────────
_API_KEY = os.environ.get("API_KEY", "")

def verificar_api_key(x_api_key: str = Header(..., description="Chave de acesso da API")):
    if not _API_KEY:
        raise HTTPException(status_code=500, detail="API_KEY não configurada no servidor")
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente")

# ─── Configuração Supabase ───────────────────────────────────────────────────
SUPABASE_URL     = os.environ.get("SUPABASE_URL", "https://bdtqjnljceskevsuqyln.supabase.co")
SUPABASE_KEY     = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET  = "pdfs"

# ─── Logos embutidos em base64 ───────────────────────────────────────────────
_LOGO_TOMBINI_B64 = "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"

_LOGO_SMOKE_B64 = "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"

def _logo_img(b64_data: str, width_mm: float, height_mm: float) -> Image:
    """Cria um objeto Image do ReportLab a partir de dados base64."""
    data = base64.b64decode(b64_data)
    img = Image(io.BytesIO(data), width=width_mm*mm, height=height_mm*mm)
    return img

# ─── Modelo de dados ────────────────────────────────────────────────────────
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
    resultado: str          # "APROVADO" ou "REPROVADO"
    responsavel: Optional[str] = "001 – Samantha B. P. Pinez"
    opacimetro_modelo: Optional[str] = "Smoke Check 2000"
    opacimetro_serial: Optional[str] = "53.558"
    opacimetro_valido_ate: Optional[str] = "07/11/2025"
    software_versao: Optional[str] = "4.0.4"

# ─── Estilos ────────────────────────────────────────────────────────────────
def S(name, size=9, bold=False, align=TA_LEFT, color=colors.black, leading=None):
    kwargs = dict(fontSize=size,
                  fontName='Helvetica-Bold' if bold else 'Helvetica',
                  textColor=color, alignment=align)
    if leading: kwargs['leading'] = leading
    return ParagraphStyle(name, **kwargs)

def P(txt, size=9, bold=False, align=TA_LEFT):
    return Paragraph(str(txt), S(f'_p{abs(hash(str(txt)+str(size)+str(bold)))}',
                                  size=size, bold=bold, align=align))

TS_PLAIN = TableStyle([
    ('TOPPADDING',    (0,0), (-1,-1), 2),
    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ('LEFTPADDING',   (0,0), (-1,-1), 2),
    ('RIGHTPADDING',  (0,0), (-1,-1), 2),
    ('VALIGN',        (0,0), (-1,-1), 'TOP'),
])

def secao(titulo, W, extra=''):
    texto = f'<b>{titulo}</b>'
    if extra: texto += f'&nbsp;&nbsp;&nbsp;&nbsp;{extra}'
    return [
        Paragraph(texto, S('sh', size=10)),
        HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=3),
    ]

# ─── Geração do PDF ─────────────────────────────────────────────────────────
def gerar_pdf(d: dict, filepath: str):
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=10*mm, bottomMargin=10*mm)
    story = []
    W = 174*mm

    # LOGO + CABEÇALHO
    logo = _logo_img(_LOGO_TOMBINI_B64, 45, 16)
    logo.hAlign = 'CENTER'
    story.append(logo)
    story.append(Spacer(1, 2*mm))

    for txt in [
        'Tombini &amp; Cia. LTDA, CNPJ/CPF: 82.809.088/0017-19',
        'Endereço: Avenida Emilio Checchinato, 1551 - Sao Roque da Chave, Itupeva - SP, 13295-274',
        'Fone: (11) 45252575 - eng.trabalho@grupotombini.com.br',
    ]:
        story.append(Paragraph(txt, S('hdr', size=8, align=TA_CENTER)))

    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph('<b>Ensaio Armazenado Opacímetro 28</b>',
                            S('titulo', size=11, align=TA_CENTER)))
    story.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=4))
    story.append(Spacer(1, 2*mm))

    # DADOS DO VEÍCULO
    story += secao('Dados do Veículo', W)
    story.append(Spacer(1, 2*mm))
    vdata = [
        [P('Marca:'),      P(d['marca']),   P('Limite Marcha Lenta:'),  P(d.get('lim_marcha_lenta','450 - 750'),    align=TA_RIGHT)],
        [P('Modelo:'),     P(d['modelo']),  P('Limite Rotação Corte:'), P(d.get('lim_rotacao_corte','2350 - 2450'), align=TA_RIGHT)],
        [P('Tipo Motor:'), P(''),           P('Limite Opacidade:'),     P(d.get('lim_opacidade','1,08'),            align=TA_RIGHT)],
        [Paragraph(f"Placa: <b>{d['placa']}</b>   Km Atual: {d['km_atual']}   Fabricação: {d['fabricacao']}", S('pl', size=9)),
         '', P('Limite Ruído:'), P(d.get('lim_ruido','89'), align=TA_RIGHT)],
    ]
    tv = Table(vdata, colWidths=[20*mm, 72*mm, 52*mm, 30*mm])
    tv.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 0), ('RIGHTPADDING',  (0,0), (-1,-1), 2),
        ('SPAN',          (0,3), (1,3)),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW',     (0,-1), (-1,-1), 0.5, colors.HexColor('#AAAAAA')),
    ]))
    story.append(tv)
    story.append(Spacer(1, 3*mm))

    # DADOS DO CLIENTE
    story += secao('Dados do Cliente', W)
    story.append(Spacer(1, 2*mm))
    for txt in [
        'Grupo Tombini - CNPJ/CPF: 82.809.088/0017-19',
        'Endereço: Avenida Emilio Checchinato, 1551 - Sao Roque da Chave, Itupeva - SP, 13295-274',
        'eng.trabalho@grupotombini.com.br',
    ]:
        story.append(Paragraph(txt, S('cli', size=9, align=TA_CENTER)))
    story.append(Spacer(1, 3*mm))

    # DADOS DO ENSAIO
    story += secao('Dados do Ensaio', W, extra=f'Início: {d["data_ensaio"]}')
    story.append(Spacer(1, 2*mm))
    t_e1 = Table([[
        Paragraph('<b>Ruído Aferido:</b>  0,00', S('e1')),
        Paragraph('<b>Altitude:</b>  Acima de 350m', S('e2', align=TA_CENTER)),
        Paragraph('<b>Temperatura Aferida:</b>  0,00°C', S('e3', align=TA_RIGHT)),
    ]], colWidths=[55*mm, 65*mm, 54*mm])
    t_e1.setStyle(TS_PLAIN)
    story.append(t_e1)
    story.append(Paragraph('Temperatura fornecida visualmente', S('tv', align=TA_CENTER)))
    story.append(Spacer(1, 1*mm))
    t_e2 = Table([[
        Paragraph('RPM Marcha Lenta Tolerada: 350 - 850', S('rpmml')),
        Paragraph('Rotação de Corte Tolerada: 2150 - 2550', S('rpmc')),
    ]], colWidths=[90*mm, 84*mm])
    t_e2.setStyle(TS_PLAIN)
    story.append(t_e2)
    story.append(Spacer(1, 3*mm))

    # TABELA DE ACELERAÇÕES
    TACC_W = 80*mm
    hs = S('th', size=9, bold=True, align=TA_CENTER)
    vs = S('tv2', size=9, bold=True, align=TA_CENTER)
    acc_data = [[Paragraph('<b>Aceleração</b>', hs),
                 Paragraph('<b>Opacidade K(m<super>-1</super>)</b>', hs)]]
    for i, v in enumerate([d['ensaio_1'], d['ensaio_2'], d['ensaio_3'], d['ensaio_4']], 1):
        acc_data.append([Paragraph(str(i), vs), Paragraph(str(v), vs)])
    t_acc = Table(acc_data, colWidths=[TACC_W/2, TACC_W/2])
    t_acc.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 1,   colors.black),
        ('INNERGRID',     (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
    ]))
    outer = Table([[t_acc]], colWidths=[W])
    outer.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),
                                ('TOPPADDING',(0,0),(-1,-1),0),
                                ('BOTTOMPADDING',(0,0),(-1,-1),0)]))
    story.append(outer)
    story.append(Spacer(1, 4*mm))

    # RESULTADO
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    cor_res = colors.HexColor('#1E8449') if d['resultado'] == 'APROVADO' else colors.HexColor('#C0392B')
    t_res = Table([[
        Paragraph('<b>Resultado do Veículo</b>', S('rvl', size=10)),
        Paragraph(f'<b>{d["placa"]}</b>',        S('rvp', size=10)),
        Paragraph(f'<b>Média: {d["media_opacidade"]}</b>', S('rvm', size=10)),
        Paragraph(f'<b>{d["resultado"]}</b>', S('rvr', size=11, color=cor_res)),
    ]], colWidths=[48*mm, 30*mm, 40*mm, 56*mm])
    t_res.setStyle(TableStyle([
        ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),2), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    story.append(t_res)
    story.append(HRFlowable(width=W, thickness=1, color=colors.black))
    story.append(Spacer(1, 4*mm))

    # DATAS + RESPONSÁVEL
    t_dt = Table([
        [Paragraph(f'<b>{d["data_ensaio"]}</b>', S('dtv', align=TA_CENTER)),
         Paragraph(f'<b>{d["validade"]}</b>', S('vdv', align=TA_CENTER)),
         Paragraph(f'Responsável: {d.get("responsavel","001 – Samantha B. P. Pinez")}', S('resp'))],
        [Paragraph('Data do Ensaio', S('dtl', size=8, align=TA_CENTER)),
         Paragraph('Validade', S('vdl', size=8, align=TA_CENTER)), ''],
    ], colWidths=[42*mm, 42*mm, 90*mm])
    t_dt.setStyle(TableStyle([
        ('LINEABOVE',     (0,0), (1,0), 0.8, colors.black),
        ('TOPPADDING',    (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('ALIGN',         (0,0), (1,-1), 'CENTER'),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_dt)
    story.append(Spacer(1, 4*mm))

    # OBSERVAÇÃO
    story.append(Paragraph('Observação:', S('obs')))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor('#AAAAAA'), spaceAfter=2))
    story.append(Spacer(1, 8*mm))

    # DADOS DO OPACÍMETRO
    story += secao('Dados do Opacímetro/Software', W)
    story.append(Spacer(1, 2*mm))
    textos_opc = [
        f'Opacímetro Modelo: {d.get("opacimetro_modelo","Smoke Check 2000")}   Serial: {d.get("opacimetro_serial","53.558")}   Válido até: {d.get("opacimetro_valido_ate","07/11/2025")}',
        'Tacômetro  Serial:',
        'Fabricante: Altanova Industrial e Comercial EIRELI EPP.',
        f'Software Syscon Versão {d.get("software_versao","4.0.4")}',
    ]
    col_txt = [[Paragraph(t, S(f'opc{i}', size=9))] for i, t in enumerate(textos_opc)]
    logo_smoke = _logo_img(_LOGO_SMOKE_B64, 35, 12)
    t_opc = Table([[col_txt, logo_smoke]], colWidths=[130*mm, 44*mm])
    t_opc.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('LEFTPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(t_opc)
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('Pág. 1 de 1',
        S('rod', size=8, align=TA_RIGHT, color=colors.grey)))

    doc.build(story)

# ─── Upload Supabase Storage ────────────────────────────────────────────────
def upload_supabase(filepath: str, filename: str) -> str:
    """Faz upload do PDF para o Supabase Storage e retorna a URL pública."""
    with open(filepath, 'rb') as f:
        conteudo = f.read()

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/pdf",
        "x-upsert": "true",   # sobrescreve se já existir
    }
    resp = requests.post(url, headers=headers, data=conteudo)
    if resp.status_code not in (200, 201):
        raise Exception(f"Erro upload Supabase: {resp.status_code} – {resp.text}")

    url_publica = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    return url_publica

# ─── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "msg": "Tombini PDF API v3 – POST /gerar-pdf"}

@app.post("/gerar-pdf", dependencies=[Depends(verificar_api_key)])
def gerar_pdf_endpoint(dados: DadosEnsaio):
    """
    Recebe JSON com dados do ensaio.
    Gera o PDF no formato Tombini, faz upload no Supabase
    e devolve o link público para o Bubble.
    """
    try:
        # Nome único: placa + uuid curto
        uid = str(uuid.uuid4())[:8]
        filename = f"{dados.placa}_{uid}.pdf"

        # Gera o PDF em arquivo temporário
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        gerar_pdf(dados.dict(), tmp.name)

        # Faz upload e pega URL
        url_pdf = upload_supabase(tmp.name, filename)

        # Limpa arquivo temporário
        os.unlink(tmp.name)

        return JSONResponse(content={
            "success": True,
            "url": url_pdf,
            "placa": dados.placa,
            "filename": filename,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
