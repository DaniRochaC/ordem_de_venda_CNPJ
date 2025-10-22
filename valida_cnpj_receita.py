import streamlit as st
import pandas as pd
import re
import requests
from PIL import Image
import base64
from io import BytesIO

# ======== Função para extrair CNPJ ========
def extrair_cnpj(texto):
    padrao = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
    return re.findall(padrao, str(texto))

# ======== Consulta à Receita Federal ========
def consultar_receita(cnpj):
    try:
        url = f"https://publica.cnpj.ws/cnpj/{re.sub(r'[^0-9]', '', cnpj)}"
        resposta = requests.get(url, timeout=10)

        if resposta.status_code == 200:
            dados = resposta.json()

            municipio = (
                dados.get("estabelecimento", {}).get("cidade", {}).get("nome", "")
                or dados.get("municipio", "")
                or ""
            )

            return {
                "CNPJ": cnpj or "",
                "Razão Social (Receita)": dados.get("razao_social", "") or "",
                "Município (Receita)": municipio,
                "Situação Cadastral": dados.get("descricao_situacao_cadastral", "Ativo") or ""
            }
        else:
            return {
                "CNPJ": cnpj or "",
                "Razão Social (Receita)": "",
                "Município (Receita)": "",
                "Situação Cadastral": "Não encontrado na Receita"
            }
    except Exception as e:
        return {
            "CNPJ": cnpj or "",
            "Razão Social (Receita)": "",
            "Município (Receita)": "",
            "Situação Cadastral": f"Erro: {str(e)}"
        }

# ======== Função para converter imagem em base64 (para exibir no HTML) ========
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# ======== Configuração da Página ========
st.set_page_config(page_title="Validador de CNPJs - Receita Federal", layout="wide")
st.markdown(
    """
    <h2 style='text-align: center;'>🧾 Validação Arquivo e Receita - Ordem de Venda</h2>
    <p style='text-align: center; font-size:16px;'>
        Faça o upload do seu arquivo Excel e verifique automaticamente se os CNPJs, Razão Social e Município estão corretos.
    </p>
    """,
    unsafe_allow_html=True
)

# ======== Upload do Arquivo ========
arquivo = st.file_uploader("📂 Selecione seu arquivo Excel", type=["xlsx", "xls"])

if arquivo:
    df = pd.read_excel(arquivo, header=None)

    if df.shape[1] > 1:
        df = df.iloc[:, 1:]

    df = df.fillna("")

    st.markdown("---")
    st.subheader("📋 Prévia dos Dados do Arquivo Excel")
    st.dataframe(df, use_container_width=True, height=400)

    # ======== Extração de CNPJs ========
    cnpjs_encontrados = []
    for linha in df.values:
        for celula in linha:
            cnpjs = extrair_cnpj(celula)
            if cnpjs:
                cnpjs_encontrados.extend(cnpjs)

    cnpjs_unicos = list(set(cnpjs_encontrados))

    if not cnpjs_unicos:
        st.warning("⚠️ Nenhum CNPJ encontrado no arquivo.")
    else:
        st.success(f"✅ {len(cnpjs_unicos)} CNPJ(s) encontrados. Iniciando validação...")

        resultados = []
        progresso = st.progress(0)

        for i, cnpj in enumerate(cnpjs_unicos):
            receita = consultar_receita(cnpj)

            cnpj_receita = receita.get("CNPJ", "")
            razao_receita = receita.get("Razão Social (Receita)", "")
            municipio_receita = receita.get("Município (Receita)", "")
            situacao_receita = receita.get("Situação Cadastral", "")

            cnpj_confere = any(cnpj_receita in str(celula) for celula in df.values.flatten())
            razao_confere = (
                any(razao_receita.lower() in str(celula).lower() for celula in df.values.flatten())
                if razao_receita else False
            )
            municipio_confere = (
                any(municipio_receita.lower() in str(celula).lower() for celula in df.values.flatten())
                if municipio_receita else False
            )

            resultados.append({
                "Informação": f"CNPJ: {cnpj_receita}",
                "Confere": "Sim" if cnpj_confere else "Não"
            })
            resultados.append({
                "Informação": f"Razão Social: {razao_receita or '-'}",
                "Confere": "Sim" if razao_confere else "Não"
            })
            resultados.append({
                "Informação": f"Município: {municipio_receita or '-'}",
                "Confere": "Sim" if municipio_confere else "Não"
            })
            resultados.append({
                "Informação": f"Situação Cadastral: {situacao_receita or '-'}",
                "Confere": ""
            })

            progresso.progress((i + 1) / len(cnpjs_unicos))

        df_resultados = pd.DataFrame(resultados)

        st.markdown("---")

        # ======== Mostra logo + título (com link e bordas arredondadas) ========
        col1, col2 = st.columns([0.15, 1])
        with col1:
            try:
                img_base64 = get_base64_image("receita_logo.png")
                st.markdown(
                    f"""
                    <a href="https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/Cnpjreva_Solicitacao.asp?cnpj=57755217000129" target="_blank">
                        <img src="data:image/png;base64,{img_base64}" width="300" style="border-radius: 12px;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )
            except Exception:
                st.write("⚠️ Logo não encontrado.")
        with col2:
            st.subheader("Informações da Receita Federal")

        # ======== Espaçamento entre imagem e tabela ========
        st.markdown("<br>", unsafe_allow_html=True)

        # ======== Exibe tabela ========
        st.dataframe(df_resultados, use_container_width=True)

        # ======== Botão para baixar CSV ========
        csv = df_resultados.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="💾 Baixar Resultado em CSV",
            data=csv,
            file_name="resultado_validacao_cnpj.csv",
            mime="text/csv"
        )

else:
    st.info("⬆️ Envie um arquivo Excel para iniciar a validação.")
