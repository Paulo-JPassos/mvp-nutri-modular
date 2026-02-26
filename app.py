import os
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

DATA_DIR = "data"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.csv")
CONSULTS_FILE = os.path.join(DATA_DIR, "consultations.csv")
REPORTS_FILE = os.path.join(DATA_DIR, "reports.csv")


def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PATIENTS_FILE):
        pd.DataFrame(columns=["patient_id", "name", "age", "sex", "created_at"]).to_csv(PATIENTS_FILE, index=False)
    if not os.path.exists(CONSULTS_FILE):
        pd.DataFrame(columns=["consult_id", "patient_id", "module", "complaint", "goals", "notes", "created_at"]).to_csv(
            CONSULTS_FILE, index=False
        )
    if not os.path.exists(REPORTS_FILE):
        pd.DataFrame(
            columns=["report_id", "consult_id", "module", "summary", "attention_points", "next_steps", "created_at"]
        ).to_csv(REPORTS_FILE, index=False)


def load_df(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def save_df(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def generate_report_simulated(module: str, complaint: str, goals: str, notes: str, extra: dict) -> dict:
    summary = f"Queixa principal: {complaint.strip()}\nObjetivos: {goals.strip()}\nObservações: {notes.strip()}"

    attention = []
    next_steps = []

    if "cansaço" in complaint.lower() or "fadiga" in complaint.lower():
        attention.append("Investigar padrão de sono, ingestão hídrica e regularidade alimentar.")
        next_steps.append("Registrar rotina de sono e hidratação por 7 dias; revisar distribuição de refeições.")

    if "emagrec" in goals.lower():
        attention.append("Risco de estratégias restritivas e baixa adesão se metas forem agressivas.")
        next_steps.append("Definir metas graduais e indicadores de adesão (frequência alimentar, proteína/dia).")

    if module == "Clínica":
        comorb = extra.get("comorbidities", "")
        labs = extra.get("labs", "")
        if comorb.strip():
            attention.append(f"Comorbidades registradas: {comorb.strip()}. Ajustar plano conforme condição clínica.")
            next_steps.append("Revisar histórico medicamentoso e sinais de intolerâncias relatadas.")
        if labs.strip():
            attention.append(f"Exames mencionados: {labs.strip()}. Verificar alterações relevantes para conduta.")
            next_steps.append("Padronizar registro de exames e acompanhar tendência longitudinal.")

    if module == "Esportiva":
        training = extra.get("training_routine", "")
        goal_perf = extra.get("performance_goal", "")
        if training.strip():
            attention.append(f"Rotina de treino: {training.strip()}. Ajustar timing de nutrientes e recuperação.")
            next_steps.append("Mapear janela pré e pós-treino; registrar percepção de esforço e recuperação.")
        if goal_perf.strip():
            attention.append(f"Meta esportiva: {goal_perf.strip()}. Alinhar ingestão energética e periodização.")
            next_steps.append("Definir indicadores de performance e plano de monitoramento semanal.")

    if not attention:
        attention = ["Não foram identificados pontos críticos com base nos dados informados; recomenda-se completar o registro."]
    if not next_steps:
        next_steps = ["Completar anamnese e estabelecer plano inicial com monitoramento de adesão em 7 a 14 dias."]

    return {
        "summary": summary,
        "attention_points": "\n".join([f"- {x}" for x in attention]),
        "next_steps": "\n".join([f"- {x}" for x in next_steps]),
    }


def main():
    st.set_page_config(page_title="MVP Nutri Modular", layout="wide")
    ensure_storage()

    if "module" not in st.session_state:
        st.session_state.module = None
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None
    if "last_consult_id" not in st.session_state:
        st.session_state.last_consult_id = None

    st.title("MVP Plataforma Modular para Nutricionistas")
    st.caption("Fluxo demonstrável: onboarding → paciente → consulta → analisar → relatório")

    st.sidebar.header("Onboarding")
    module = st.sidebar.selectbox("Selecione a área de atuação (módulo)", ["", "Clínica", "Esportiva"])
    if module:
        st.session_state.module = module
        st.sidebar.success(f"Módulo ativo: {module}")
    else:
        st.sidebar.info("Selecione um módulo para começar.")

    col1, col2 = st.columns([1, 1])

    with col1:
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

    with col2:
        st.subheader("2) Consulta e análise")
        if not st.session_state.module:
            st.warning("Selecione um módulo no onboarding para liberar o formulário de consulta.")
            st.stop()
        if not st.session_state.patient_id:
            st.warning("Cadastre ou selecione um paciente para registrar a consulta.")
            st.stop()

        st.write(f"Módulo ativo: **{st.session_state.module}**")
        st.write(f"Paciente selecionado: **{st.session_state.patient_id}**")

        with st.form("consult_form", clear_on_submit=False):
            complaint = st.text_input("Queixa principal")
            goals = st.text_input("Objetivos do acompanhamento")
            notes = st.text_area("Observações adicionais", height=120)

            extra = {}
            if st.session_state.module == "Clínica":
                extra["comorbidities"] = st.text_input("Comorbidades (opcional)")
                extra["labs"] = st.text_input("Exames laboratoriais citados (opcional)")
            if st.session_state.module == "Esportiva":
                extra["training_routine"] = st.text_input("Rotina de treino (opcional)")
                extra["performance_goal"] = st.text_input("Meta esportiva (opcional)")

            save_consult_btn = st.form_submit_button("Salvar consulta")
            analyze_btn = st.form_submit_button("Analisar consulta")

        consults = load_df(CONSULTS_FILE)
        reports = load_df(REPORTS_FILE)

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
                    "complaint": complaint.strip(),
                    "goals": goals.strip(),
                    "notes": notes.strip(),
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
                row = {
                    "consult_id": cid,
                    "patient_id": st.session_state.patient_id,
                    "module": st.session_state.module,
                    "complaint": complaint.strip(),
                    "goals": goals.strip(),
                    "notes": notes.strip(),
                    "created_at": now,
                }
                consults = pd.concat([consults, pd.DataFrame([row])], ignore_index=True)
                save_df(consults, CONSULTS_FILE)
                st.session_state.last_consult_id = cid

                report = generate_report_simulated(st.session_state.module, complaint, goals, notes, extra)

                rid = str(uuid.uuid4())[:8]
                report_row = {
                    "report_id": rid,
                    "consult_id": cid,
                    "module": st.session_state.module,
                    "summary": report["summary"],
                    "attention_points": report["attention_points"],
                    "next_steps": report["next_steps"],
                    "created_at": now,
                }
                reports = pd.concat([reports, pd.DataFrame([report_row])], ignore_index=True)
                save_df(reports, REPORTS_FILE)

                st.success("Relatório gerado com sucesso. Resultado observável abaixo:")

                st.markdown("### 3) Resultado observável: Relatório estruturado")
                st.markdown("**Síntese**")
                st.code(report["summary"])
                st.markdown("**Pontos de atenção**")
                st.markdown(report["attention_points"])
                st.markdown("**Próximos passos sugeridos**")
                st.markdown(report["next_steps"])

        st.divider()
        st.subheader("Histórico mínimo")
        consults = load_df(CONSULTS_FILE)
        if len(consults) > 0:
            p_consults = consults[consults["patient_id"] == st.session_state.patient_id].copy()
            if len(p_consults) == 0:
                st.info("Nenhuma consulta registrada para este paciente.")
            else:
                p_consults = p_consults.sort_values("created_at", ascending=False)
                st.dataframe(p_consults[["created_at", "consult_id", "module", "complaint", "goals"]], use_container_width=True)
        else:
            st.info("Ainda não há consultas registradas.")


if __name__ == "__main__":
    main()