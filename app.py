import re
import random
from PyPDF2 import PdfReader
from flask import Flask, render_template, request, redirect, send_file, url_for

app = Flask(__name__)

# Função para extrair as questões e o gabarito
def extrair_questoes_e_gabarito(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        questoes = []
        gabarito = {}
        for page in reader.pages:
            text = page.extract_text()
            padrao_questao = r'(\d+)\.\s*\((.*?)\/(\d{4})\)\s*\n\s*(.*?)\s*(a\)\s*[\s\S]*?)(?=\n\d+\.\s*\(.*?\/\d{4}\)|\Z)'
            matches_questao = re.findall(padrao_questao, text, re.DOTALL)
            for i in range(len(matches_questao)):
                questao = (
                    re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '', matches_questao[i][0]), 
                    re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '', matches_questao[i][1]), 
                    re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '', matches_questao[i][2]),
                    re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '', matches_questao[i][3]),
                    re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '', matches_questao[i][4])
                )
                # Verifica se a questão tem alternativas
                if 'a)' in questao[4]:
                    questoes.append(questao)
            padrao_gabarito = r'(\d+)\.\s*([a-eA-E]|Anulada)'
            matches_gabarito = re.findall(padrao_gabarito, text)
            for numero, resposta in matches_gabarito:
                gabarito[numero] = resposta.strip()
    return questoes, gabarito

# Função para criar as alternativas de acordo com o número fornecido
def criar_alternativas(numero, alternativas_lista):
    letras = ['a', 'b', 'c', 'd', 'e']
    alternativas_html = ''
    for i, alternativa in enumerate(alternativas_lista):
        if i >= len(letras):
            break
        letra = letras[i]
        alternativas_html += f"""
                    <div class="form-check alternativa">
                        <input class="form-check-input" type="radio" name="alternativa_{numero}" id="alternativa_{numero}_{letra}" value="{letra}">
                        <label class="form-check-label" for="alternativa_{numero}_{letra}">{alternativa.strip()}</label>
                    </div>"""
    return alternativas_html

# Função para criar o HTML com as questões, alternativas e gabarito
def criar_html_questoes(questoes, gabarito, valor_gabarito):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Questões</title>
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
            .instituicao {
                font-weight: bold;
            }
            .escopo {
                font-style: italic;
            }
            .alternativa {
                margin-left: 20px;
            }
        </style>
        <script>
            var respostasCorretas = {
    """
    
    for numero, resposta in gabarito.items():
        html_content += f'"{numero}": "{resposta.lower()}",\n'
    
    html_content += """
            };

            function atualizarGabarito(numero, respostaSelecionada) {
                var gabaritoInput = document.getElementById('gabarito_' + numero);
                gabaritoInput.value = respostaSelecionada;
            }

            function verificarResposta(numero) {
                var respostaSelecionada = document.querySelector('input[name="alternativa_' + numero + '"]:checked');
                if (respostaSelecionada) {
                    var respostaUsuario = respostaSelecionada.value;
                    if (respostaUsuario === respostasCorretas[numero]) {
                        alert("Resposta correta!");
                    } else {
                        alert("Resposta incorreta.");
                    }
                    atualizarGabarito(numero, respostaUsuario);
                } else {
                    alert("Selecione uma alternativa.");
                }
            }
        </script>
    </head>
    <body>
        <div class="container">
    """
    
    questoes_selecionadas = set()  # Conjunto para manter controle das questões já selecionadas
    escopos_selecionados = set()  # Conjunto para manter controle dos escopos já selecionados
    
    for questao in questoes:
        numero, instituicao, ano, escopo, alternativas = questao
        
        if escopo not in escopos_selecionados:
            escopos_selecionados.add(escopo)
        else:
            continue
        
        html_content += f"""
            <div class="card mt-3">
                <div class="card-body">
                    <h5 class="card-title">Questão {numero}:</h5>
                    <p class="card-text instituicao_ano">{instituicao} / {ano}</p>
                    <p class="card-text escopo">{escopo}</p>
                    <div class="form-group">"""
        
        alternativas_lista = alternativas.split('\n')
        alternativas_html = criar_alternativas(numero, alternativas_lista)
        html_content += alternativas_html
        
        html_content += f"""
                    </div>
                    <input type="hidden" id="gabarito_{numero}" name="gabarito_{numero}" value="{valor_gabarito}">
                    <button class="btn btn-primary" onclick="verificarResposta('{numero}')">Verificar Resposta</button>
                </div>
            </div>
        """
    
    html_content += """
        </div>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.16.0/umd/popper.min.js"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
    </body>
    </html>
    """

    return html_content

# Função para remover CPF do HTML
def remover_cpf(html):
    html = re.sub(r'CPF\s*\d{11}', '', html)
    return html

# Função para ordenar as questões
def ordenar_questoes(questoes):
    return sorted(questoes, key=lambda questao: int(questao[0]))

# Rota para a página inicial
@app.route('/')
def index():
    return send_file('index.html')

# Rota para processar o upload do arquivo PDF
@app.route('/processar_pdf', methods=['POST'])
def processar_pdf():
    if 'file' not in request.files:
        return redirect('/')
    
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    
    if file:
        pdf_path = 'uploaded_file.pdf'
        file.save(pdf_path)
        
        # Extrai as questões e o gabarito do PDF
        questoes, gabarito = extrair_questoes_e_gabarito(pdf_path)
        
        # Defina o valor do gabarito que você deseja utilizar
        valor_gabarito = "resposta_correspondente"
        
        # Ordena as questões
        questoes_ordenadas = ordenar_questoes(questoes)
        
        # Cria o HTML com as questões, alternativas e gabarito, passando o valor_gabarito
        html_content = criar_html_questoes(questoes_ordenadas, gabarito, valor_gabarito)
        
        # Remove CPF do HTML
        html_content = remover_cpf(html_content)
        
        # Atualiza o arquivo HTML de resultado existente com o conteúdo das questões
        with open('resultado.html', 'w', encoding='utf-8') as resultado_file:
            resultado_file.write(html_content)
        
        return redirect(url_for('resultado'))

# Rota para a página de resultados
@app.route('/resultado')
def resultado():
    # Retorna o arquivo HTML de resultado existente
    return send_file('resultado.html')

if __name__ == '__main__':
    app.run(debug=True)