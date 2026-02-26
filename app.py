# =========================
# NutriApp - MVP Modular (Streamlit)
# =========================

import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Tuple

import pandas as pd
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


# =========================
# 1) CONFIGURAÇÃO E STORAGE
# =========================

DATA_DIR = "data"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.csv")
CONSULTS_FILE = os.path.join(DATA_DIR, "consultations.csv")
REPORTS_FILE = os.path.join(DATA_DIR, "reports.csv")


def ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(PATIENTS_FILE):
        pd.DataFrame(columns=["patient_id", "name", "age", "sex", "created_at"]).to_csv(PATIENTS_FILE, index=False)

    if not os.path.exists(CONSULTS_FILE):
        pd.DataFrame(
            columns=[
                "consult_id", "patient_id", "module", "subtype",
                "complaint", "goals", "notes", "extra_json", "created_at"
            ]
        ).to_csv(CONSULTS_FILE, index=False)

    if not os.path.exists(REPORTS_FILE):
        pd.DataFrame(
            columns=[
                "report_id", "consult_id", "patient_id", "module", "subtype",
                "summary", "assessment", "attention_points",
                "next_steps", "missing_data", "follow_up",
                "created_at"
            ]
        ).to_csv(REPORTS_FILE, index=False)


def load_df(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def save_df(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


# =========================
# 2) DEDUPLICAÇÃO
# =========================

def deduplicate_storage() -> Dict[str, Tuple[int, int]]:
    summary: Dict[str, Tuple[int, int]] = {}

    p = load_df(PATIENTS_FILE)
    before = len(p)
    if before > 0 and "created_at" in p.columns:
        p = p.sort_values("created_at", ascending=True)
        p = p.drop_duplicates(subset=["name", "age", "sex"], keep="first")
        save_df(p, PATIENTS_FILE)
    summary["patients"] = (before, len(p))

    c_df = load_df(CONSULTS_FILE)
    before = len(c_df)
    if before > 0 and "created_at" in c_df.columns:
        c_df = c_df.sort_values("created_at", ascending=True)
        c_df = c_df.drop_duplicates(
            subset=["patient_id", "module", "subtype", "complaint", "goals", "notes", "extra_json"],
            keep="first"
        )
        save_df(c_df, CONSULTS_FILE)
    summary["consultations"] = (before, len(c_df))

    r = load_df(REPORTS_FILE)
    before = len(r)
    if before > 0 and "created_at" in r.columns:
        r = r.sort_values("created_at", ascending=True)
        r = r.drop_duplicates(
            subset=[
                "patient_id", "module", "subtype",
                "summary", "assessment", "attention_points",
                "next_steps", "missing_data", "follow_up"
            ],
            keep="first"
        )
        save_df(r, REPORTS_FILE)
    summary["reports"] = (before, len(r))

    return summary


# =========================
# 3) "IA" SIMULADA MAIS COMPLETA
# =========================

def _contains_any(text: str, terms) -> bool:
    t = (text or "").lower()
    return any(term in t for term in terms)


def generate_report_simulated(module: str, subtype: str, complaint: str, goals: str, notes: str, extra: dict) -> dict:
    complaint = (complaint or "").strip()
    goals = (goals or "").strip()
    notes = (notes or "").strip()

    summary = (
        f"Módulo: {module} ({subtype})\n"
        f"Queixa principal: {complaint}\n"
        f"Objetivos: {goals}\n"
        f"Observações: {notes if notes else 'Não informado'}"
    )

    assessment_lines = []
    attention = []
    next_steps = []
    missing = []
    follow_up = []

    # Heurísticas comuns
    if _contains_any(complaint, ["cansaço", "fadiga", "sonol", "insônia"]):
        assessment_lines.append("A queixa sugere possível relação com sono, hidratação e regularidade alimentar.")
        attention.append("Investigar padrão de sono, ingestão hídrica e regularidade das refeições.")
        next_steps.append("Registrar sono e hidratação por 7 dias e revisar distribuição das refeições ao longo do dia.")

    if _contains_any(goals, ["emagrec", "perder peso", "redução de peso"]):
        assessment_lines.append("O objetivo indica necessidade de estratégia gradual para favorecer adesão.")
        attention.append("Risco de metas agressivas reduzirem adesão e favorecerem compensações alimentares.")
        next_steps.append("Definir metas graduais e indicadores de adesão (frequência alimentar, proteína/dia e rotina).")

    if _contains_any(complaint + " " + notes, ["intest", "gases", "incha", "azia", "reflux"]):
        assessment_lines.append("Há indícios de desconforto gastrointestinal que pode demandar investigação dirigida.")
        attention.append("Avaliar gatilhos alimentares, horários e composição das refeições.")
        next_steps.append("Aplicar diário alimentar dirigido por 3 a 7 dias e registrar sintomas por horário.")

    # MÓDULO: Nutrição Clínica
    if module == "Nutrição clínica":
        comorb = (extra.get("comorbidities") or "").strip()
        labs = (extra.get("labs") or "").strip()
        meds = (extra.get("meds") or "").strip()

        assessment_lines.append("No contexto clínico, recomenda-se integrar histórico, sintomas e dados laboratoriais para orientar conduta inicial.")

        if comorb:
            attention.append(f"Comorbidades registradas: {comorb}. Ajustar conduta conforme condição clínica.")
        else:
            missing.append("Comorbidades e diagnósticos relevantes não informados.")

        if labs:
            attention.append(f"Exames citados: {labs}. Verificar alterações relevantes e tendência temporal.")
            next_steps.append("Padronizar registro de exames com datas e acompanhar tendência longitudinal.")
        else:
            missing.append("Exames laboratoriais recentes não informados, quando aplicável.")

        if meds:
            attention.append(f"Medicamentos e suplementos: {meds}. Verificar interações e impactos (apetite, glicemia, sono).")
        else:
            missing.append("Medicamentos e suplementos em uso não informados.")

        next_steps.append("Definir plano inicial com metas objetivas e rotina de acompanhamento.")
        follow_up.append("Reavaliar adesão, sintomas e evolução em 7 a 14 dias.")
        follow_up.append("Atualizar medidas e revisar exames conforme disponibilidade.")

    # MÓDULO: Nutrição Esportiva
    elif module == "Nutrição esportiva":
        training = (extra.get("training_routine") or "").strip()
        goal_perf = (extra.get("performance_goal") or "").strip()
        comp = (extra.get("body_comp") or "").strip()

        assessment_lines.append("No contexto esportivo, é necessário alinhar ingestão, timing e recuperação à rotina de treino e objetivo de performance.")

        if training:
            attention.append(f"Rotina de treino: {training}. Ajustar timing de nutrientes, hidratação e recuperação.")
            next_steps.append("Mapear janela pré e pós-treino e registrar recuperação percebida e sono.")
        else:
            missing.append("Rotina de treino (frequência, duração e intensidade) não informada.")

        if goal_perf:
            attention.append(f"Meta esportiva: {goal_perf}. Alinhar estratégia alimentar à periodização.")
        else:
            missing.append("Meta esportiva específica não informada (performance, hipertrofia, resistência, recomposição).")

        if comp:
            attention.append(f"Composição corporal: {comp}. Usar como referência para metas realistas e monitoramento.")
        else:
            missing.append("Composição corporal não informada, quando aplicável.")

        next_steps.append("Definir indicadores semanais: treinos realizados, sono, fome, recuperação e desempenho.")
        follow_up.append("Reavaliar resposta ao plano e performance em 7 dias, com ajustes finos no timing e distribuição.")
        follow_up.append("Atualizar métricas conforme periodicidade e disponibilidade.")

    # MÓDULO: Materno Infantil
    elif module == "Materno infantil":
        child_age = (extra.get("child_age") or "").strip()
        breastfeeding = (extra.get("breastfeeding") or "").strip()
        growth = (extra.get("growth_curve") or "").strip()
        allergy = (extra.get("allergy") or "").strip()

        assessment_lines.append("No contexto materno-infantil, é essencial considerar idade, rotina alimentar, crescimento e tolerâncias, priorizando segurança.")

        if child_age:
            attention.append(f"Idade da criança: {child_age}. Ajustar orientação conforme fase alimentar.")
        else:
            missing.append("Idade da criança não informada, essencial para orientar conduta.")

        if breastfeeding:
            attention.append(f"Aleitamento: {breastfeeding}. Considerar manejo e orientação conforme rotina familiar.")
        else:
            missing.append("Informação sobre aleitamento não informada, quando aplicável.")

        if growth:
            attention.append(f"Crescimento/curva: {growth}. Verificar tendência e sinais de risco nutricional.")
            next_steps.append("Registrar medidas com datas e acompanhar tendência longitudinal na curva.")
        else:
            missing.append("Peso/estatura e datas não informados.")

        if allergy:
            attention.append(f"Alergias/intolerâncias: {allergy}. Garantir adequação e segurança alimentar.")
        else:
            missing.append("Alergias/intolerâncias não informadas, quando aplicável.")

        next_steps.append("Orientar plano inicial considerando rotina familiar, aceitação alimentar e segurança na variedade.")
        follow_up.append("Reavaliar aceitação e evolução em 14 a 30 dias, conforme caso.")

    if not assessment_lines:
        assessment_lines.append("Registro insuficiente para avaliação mais direcionada. Recomenda-se completar dados e reavaliar.")

    if not attention:
        attention = ["Não foram identificados pontos críticos com base nos dados informados. Recomenda-se completar o registro."]

    if not next_steps:
        next_steps = ["Completar anamnese e estabelecer plano inicial com monitoramento em 7 a 14 dias."]

    if not missing:
        missing = ["Sem pendências críticas identificadas a partir do registro atual."]

    if not follow_up:
        follow_up = ["Agendar retorno para reavaliação e ajuste do plano conforme evolução e adesão."]

    return {
        "summary": summary,
        "assessment": "\n".join([f"- {x}" for x in assessment_lines]),
        "attention_points": "\n".join([f"- {x}" for x in attention]),
        "next_steps": "\n".join([f"- {x}" for x in next_steps]),
        "missing_data": "\n".join([f"- {x}" for x in missing]),
        "follow_up": "\n".join([f"- {x}" for x in follow_up]),
    }


# =========================
# 4) PDF (REPORTLAB)
# =========================

def _wrap_text(text: str, max_chars: int = 105) -> list:
    if not text:
        return [""]
    words = text.replace("\r", "").split()
    lines, line = [], []
    count = 0
    for w in words:
        add = len(w) + (1 if count > 0 else 0)
        if count + add <= max_chars:
            line.append(w)
            count += add
        else:
            lines.append(" ".join(line))
            line = [w]
            count = len(w)
    if line:
        lines.append(" ".join(line))
    return lines


def generate_report_pdf_bytes(
    module: str,
    subtype: str,
    patient_id: str,
    consult_id: str,
    created_at: str,
    report: dict,
    patient_name: Optional[str] = None,
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    x_left = 2 * cm
    y = height - 2 * cm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_left, y, "NutriApp - Relatório do Atendimento")
    y -= 0.8 * cm

    c.setFont("Helvetica", 10)
    header_lines = [
        f"Módulo: {module} ({subtype})",
        f"Paciente: {patient_name} (ID {patient_id})" if patient_name else f"Paciente ID: {patient_id}",
        f"Consulta ID: {consult_id}",
        f"Data/Hora: {created_at}",
    ]
    for line in header_lines:
        c.drawString(x_left, y, line)
        y -= 0.55 * cm

    y -= 0.25 * cm
    c.line(x_left, y, width - x_left, y)
    y -= 0.7 * cm

    def section(title: str, body: str):
        nonlocal y
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x_left, y, title)
        y -= 0.6 * cm
        c.setFont("Helvetica", 10)

        for ln in _wrap_text(body, max_chars=105):
            if y < 2 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Helvetica", 10)
            c.drawString(x_left, y, ln)
            y -= 0.5 * cm
        y -= 0.35 * cm

    section("Síntese", report.get("summary", ""))
    section("Avaliação inicial", report.get("assessment", ""))
    section("Pontos de atenção", report.get("attention_points", ""))
    section("Próximos passos sugeridos", report.get("next_steps", ""))
    section("Dados que faltam para refinar a análise", report.get("missing_data", ""))
    section("Sugestão de acompanhamento", report.get("follow_up", ""))

    c.setFont("Helvetica-Oblique", 8)
    disclaimer = "Observação: este relatório é gerado como apoio e não substitui o julgamento profissional."
    for ln in _wrap_text(disclaimer, max_chars=110):
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica-Oblique", 8)
        c.drawString(x_left, y, ln)
        y -= 0.45 * cm

    c.save()
    buffer.seek(0)
    return buffer.read()


# =========================
# 5) UI
# =========================

def sidebar_controls():
    st.sidebar.header("Módulos (clique para acessar)")
    c1, c2, c3 = st.sidebar.columns(3)

    if c1.button("Clínica"):
        st.session_state.module = "Nutrição clínica"
    if c2.button("Esportiva"):
        st.session_state.module = "Nutrição esportiva"
    if c3.button("Materno"):
        st.session_state.module = "Materno infantil"

    if st.session_state.module:
        st.sidebar.success(f"Módulo ativo: {st.session_state.module}")
    else:
        st.sidebar.info("Selecione um módulo para começar.")

    st.sidebar.divider()
    st.sidebar.header("Manutenção")

    if st.sidebar.button("Remover duplicatas"):
        result = deduplicate_storage()
        st.sidebar.success("Deduplicação concluída.")
        st.sidebar.write(f"Pacientes: {result['patients'][0]} → {result['patients'][1]}")
        st.sidebar.write(f"Consultas: {result['consultations'][0]} → {result['consultations'][1]}")
        st.sidebar.write(f"Relatórios: {result['reports'][0]} → {result['reports'][1]}")

    st.sidebar.divider()
    st.sidebar.header("Exportação")

    # PDF persistido na sessão
    if st.session_state.get("last_pdf_bytes"):
        st.sidebar.download_button(
            label="Baixar último PDF",
            data=st.session_state["last_pdf_bytes"],
            file_name=st.session_state.get("last_pdf_filename", "relatorio.pdf"),
            mime="application/pdf",
        )
    else:
        st.sidebar.caption("Gere um relatório para liberar o PDF.")

    # Exportar relatórios CSV (importante na nuvem)
    reports_df = load_df(REPORTS_FILE)
    if len(reports_df) > 0:
        st.sidebar.download_button(
            label="Baixar relatórios (CSV)",
            data=reports_df.to_csv(index=False).encode("utf-8"),
            file_name="reports_export.csv",
            mime="text/csv",
        )
    else:
        st.sidebar.caption("Ainda não há relatórios para exportar.")


def patient_block() -> pd.DataFrame:
    st.subheader("1) Paciente")
    patients = load_df(PATIENTS_FILE)

    with st.form("patient_form", clear_on_submit=True):
        name = st.text_input("Nome")
        age = st.number_input("Idade", min_value=0, max_value=120, value=30)
        sex = st.selectbox("Sexo", ["", "Feminino", "Masculino", "Outro/Prefiro não informar"])
        submitted = st.form_submit_button("Cadastrar paciente")

        if submitted:
            if not name.strip():
                st.error("Informe o nome do paciente.")
            else:
                pid = str(uuid.uuid4())[:8]
                now = datetime.now().isoformat(timespec="seconds")
                new_row = {"patient_id": pid, "name": name.strip(), "age": age, "sex": sex, "created_at": now}
                patients = pd.concat([patients, pd.DataFrame([new_row])], ignore_index=True)
                save_df(patients, PATIENTS_FILE)
                st.session_state.patient_id = pid
                st.success(f"Paciente cadastrado: {name} (ID {pid})")

    st.markdown("**Selecionar paciente existente**")
    if len(patients) > 0:
        options = patients.apply(lambda r: f"{r['name']} | ID {r['patient_id']}", axis=1).tolist()
        choice = st.selectbox("Pacientes", [""] + options)
        if choice:
            st.session_state.patient_id = choice.split("ID ")[1]
            st.info(f"Paciente selecionado: {choice}")
    else:
        st.info("Nenhum paciente cadastrado ainda.")

    return patients


def consult_and_analysis_block(patients: pd.DataFrame):
    st.subheader("2) Consulta e análise")

    if not st.session_state.module:
        st.warning("Selecione um módulo para liberar o formulário de consulta.")
        st.stop()

    if not st.session_state.patient_id:
        st.warning("Cadastre ou selecione um paciente para registrar a consulta.")
        st.stop()

    st.write(f"Módulo ativo: **{st.session_state.module}**")
    st.write(f"Paciente selecionado: **{st.session_state.patient_id}**")

    # Lista suspensa apenas para Clínica e Esportiva (conforme pedido)
    subtype = "Padrão"
    if st.session_state.module == "Nutrição clínica":
        subtype = st.selectbox("Tipo de consulta (Clínica)", ["Padrão", "Emagrecimento", "Diabetes/Metabólica", "Gastrointestinal"])
    elif st.session_state.module == "Nutrição esportiva":
        subtype = st.selectbox("Tipo de consulta (Esportiva)", ["Padrão", "Hipertrofia", "Performance/Resistência", "Recomposição corporal"])
    else:
        subtype = "Materno infantil"

    with st.form("consult_form", clear_on_submit=False):
        complaint = st.text_input("Queixa principal")
        goals = st.text_input("Objetivos do acompanhamento")
        notes = st.text_area("Observações adicionais", height=120)

        extra = {}

        if st.session_state.module == "Nutrição clínica":
            st.markdown("**Campos do módulo Nutrição clínica**")
            extra["comorbidities"] = st.text_input("Comorbidades (opcional)")
            extra["labs"] = st.text_input("Exames laboratoriais citados (opcional)")
            extra["meds"] = st.text_input("Medicamentos e suplementos (opcional)")

        elif st.session_state.module == "Nutrição esportiva":
            st.markdown("**Campos do módulo Nutrição esportiva**")
            extra["training_routine"] = st.text_input("Rotina de treino (opcional)")
            extra["performance_goal"] = st.text_input("Meta esportiva (opcional)")
            extra["body_comp"] = st.text_input("Composição corporal (opcional)")

        elif st.session_state.module == "Materno infantil":
            st.markdown("**Campos do módulo Materno infantil**")
            extra["child_age"] = st.text_input("Idade da criança (opcional)")
            extra["breastfeeding"] = st.text_input("Aleitamento (opcional)")
            extra["growth_curve"] = st.text_input("Crescimento/curva (opcional)")
            extra["allergy"] = st.text_input("Alergias/intolerâncias (opcional)")

        save_consult_btn = st.form_submit_button("Salvar consulta")
        analyze_btn = st.form_submit_button("Analisar consulta")

    consults = load_df(CONSULTS_FILE)
    reports = load_df(REPORTS_FILE)

    def get_patient_name() -> Optional[str]:
        if len(patients) > 0 and "patient_id" in patients.columns:
            prow = patients[patients["patient_id"] == st.session_state.patient_id]
            if len(prow) > 0:
                name = str(prow.iloc[0].get("name", "")).strip()
                return name if name else None
        return None

    if save_consult_btn:
        if not complaint.strip() or not goals.strip():
            st.error("Preencha, no mínimo, queixa principal e objetivos.")
        else:
            cid = str(uuid.uuid4())[:8]
            now = datetime.now().isoformat(timespec="seconds")
            row = {
                "consult_id": cid,
                "patient_id": st.session_state.patient_id,
                "module": st.session_state.module,
                "subtype": subtype,
                "complaint": complaint.strip(),
                "goals": goals.strip(),
                "notes": notes.strip(),
                "extra_json": str(extra),
                "created_at": now,
            }
            consults = pd.concat([consults, pd.DataFrame([row])], ignore_index=True)
            save_df(consults, CONSULTS_FILE)
            st.session_state.last_consult_id = cid
            st.success(f"Consulta salva (ID {cid}).")

    if analyze_btn:
        if not complaint.strip() or not goals.strip():
            st.error("Preencha, no mínimo, queixa principal e objetivos antes de analisar.")
        else:
            cid = str(uuid.uuid4())[:8]
            now = datetime.now().isoformat(timespec="seconds")

            # salva consulta junto com análise
            row = {
                "consult_id": cid,
                "patient_id": st.session_state.patient_id,
                "module": st.session_state.module,
                "subtype": subtype,
                "complaint": complaint.strip(),
                "goals": goals.strip(),
                "notes": notes.strip(),
                "extra_json": str(extra),
                "created_at": now,
            }
            consults = pd.concat([consults, pd.DataFrame([row])], ignore_index=True)
            save_df(consults, CONSULTS_FILE)
            st.session_state.last_consult_id = cid

            report = generate_report_simulated(st.session_state.module, subtype, complaint, goals, notes, extra)

            rid = str(uuid.uuid4())[:8]
            report_row = {
                "report_id": rid,
                "consult_id": cid,
                "patient_id": st.session_state.patient_id,
                "module": st.session_state.module,
                "subtype": subtype,
                "summary": report["summary"],
                "assessment": report["assessment"],
                "attention_points": report["attention_points"],
                "next_steps": report["next_steps"],
                "missing_data": report["missing_data"],
                "follow_up": report["follow_up"],
                "created_at": now,
            }
            reports = pd.concat([reports, pd.DataFrame([report_row])], ignore_index=True)
            save_df(reports, REPORTS_FILE)

            st.success("Relatório gerado com sucesso. Resultado observável abaixo:")

            st.markdown("### 3) Relatório estruturado")
            st.markdown("**Síntese**")
            st.code(report["summary"])
            st.markdown("**Avaliação inicial**")
            st.markdown(report["assessment"])
            st.markdown("**Pontos de atenção**")
            st.markdown(report["attention_points"])
            st.markdown("**Próximos passos sugeridos**")
            st.markdown(report["next_steps"])
            st.markdown("**Dados faltantes**")
            st.markdown(report["missing_data"])
            st.markdown("**Acompanhamento**")
            st.markdown(report["follow_up"])

            # PDF: gerar e manter em sessão
            patient_name = get_patient_name()

            try:
                pdf_bytes = generate_report_pdf_bytes(
                    module=st.session_state.module,
                    subtype=subtype,
                    patient_id=st.session_state.patient_id,
                    consult_id=cid,
                    created_at=now,
                    report=report,
                    patient_name=patient_name,
                )
            except Exception as e:
                st.error("Falha ao gerar PDF. Verifique se 'reportlab' está instalado e se o deploy foi atualizado.")
                st.exception(e)
                pdf_bytes = None

            if pdf_bytes:
                st.session_state["last_pdf_bytes"] = pdf_bytes
                st.session_state["last_pdf_filename"] = f"relatorio_{st.session_state.patient_id}_{cid}.pdf"

                # Download imediato na tela (mais confiável)
                st.download_button(
                    label="Baixar relatório (PDF)",
                    data=st.session_state["last_pdf_bytes"],
                    file_name=st.session_state["last_pdf_filename"],
                    mime="application/pdf",
                    key=f"pdf_download_{cid}",
                )

                st.info("PDF gerado e disponível também na barra lateral.")

    st.divider()
    st.subheader("Histórico mínimo (sessão atual)")
    consults = load_df(CONSULTS_FILE)
    if len(consults) > 0 and "patient_id" in consults.columns:
        p_consults = consults[consults["patient_id"] == st.session_state.patient_id].copy()
        if len(p_consults) == 0:
            st.info("Nenhuma consulta registrada para este paciente.")
        else:
            p_consults = p_consults.sort_values("created_at", ascending=False)
            st.dataframe(
                p_consults[["created_at", "consult_id", "module", "subtype", "complaint", "goals"]],
                use_container_width=True,
            )
    else:
        st.info("Ainda não há consultas registradas.")


def main():
    st.set_page_config(page_title="NutriApp", layout="wide")
    ensure_storage()

    if "module" not in st.session_state:
        st.session_state.module = None
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None
    if "last_consult_id" not in st.session_state:
        st.session_state.last_consult_id = None
    if "last_pdf_bytes" not in st.session_state:
        st.session_state.last_pdf_bytes = None
    if "last_pdf_filename" not in st.session_state:
        st.session_state.last_pdf_filename = None

    st.title("NutriApp")
    st.caption(
        "MVP demonstrável com módulos por especialidade e geração de relatório estruturado com apoio de IA simulada. "
        "Fluxo: módulo → paciente → consulta → analisar → relatório + PDF."
    )

    sidebar_controls()

    col1, col2 = st.columns([1, 1])
    with col1:
        patients = patient_block()
    with col2:
        consult_and_analysis_block(patients)


if __name__ == "__main__":
    main()
