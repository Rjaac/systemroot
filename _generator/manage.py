import os
import datetime

# --- CONFIGURAÇÕES ---
# Onde estão os ficheiros do blog
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')
TEMPLATES_DIR = os.path.join(BASE_DIR, '_generator', 'templates')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')

def create_post(title, summary, content_file):
    """
    Esta função cria um novo post no blog.
    Ela lê um ficheiro de texto, usa o template HTML e cria o ficheiro .html final.
    """
    
    # 1. Definir a data atual no formato YYYY.MM.DD (padrão do blog)
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    
    # 2. Criar um nome de ficheiro seguro a partir do título (ex: "Novo Post" -> "novo-post")
    filename = title.lower().replace(" ", "-").replace(":", "").replace("_", "-")
    
    # 3. Ler o conteúdo do seu ficheiro de texto (.txt)
    txt_path = os.path.join(POSTS_DIR, 'text_files', content_file)
    if not os.path.exists(txt_path):
        print(f"ERRO: Ficheiro de texto '{content_file}' não encontrado em posts/text_files/")
        return

    with open(txt_path, 'r', encoding='utf-8') as f:
        # Lemos o texto e substituímos quebras de linha por <p> para o HTML
        raw_content = f.read()
        formatted_content = "".join([f"<p>{line}</p>" for line in raw_content.split('\n') if line.strip()])

    # 4. Ler o Template do Post e substituir os marcadores {{...}}
    with open(os.path.join(TEMPLATES_DIR, 'post_template.html'), 'r', encoding='utf-8') as f:
        post_html = f.read()
    
    post_html = post_html.replace('{{TITLE}}', title)
    post_html = post_html.replace('{{DATE}}', date_str)
    post_html = post_html.replace('{{CONTENT}}', formatted_content)

    # 5. Guardar o novo ficheiro .html na pasta posts/
    new_post_path = os.path.join(POSTS_DIR, f"{filename}.html")
    with open(new_post_path, 'w', encoding='utf-8') as f:
        f.write(post_html)
    print(f"SUCESSO: Post criado em '{new_post_path}'")

    # 6. Atualizar a página inicial (index.html)
    update_index(title, summary, filename, date_str)

def update_index(title, summary, filename, date_str):
    """
    Esta função insere o resumo do novo post no index.html, logo abaixo do cabeçalho.
    """
    
    # Ler o Template do item da lista
    with open(os.path.join(TEMPLATES_DIR, 'index_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()
    
    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{SUMMARY}}', summary)
    item_html = item_html.replace('{{FILENAME}}', filename)
    item_html = item_html.replace('{{DATE}}', date_str)

    # Ler o index.html atual
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index_content = f.read()

    # Procurar onde inserir (logo a seguir ao <h2>LATEST TRANSMISSION_</h2>)
    marker = '<h2>LATEST TRANSMISSION_</h2>'
    if marker in index_content:
        # Dividimos o ficheiro em dois no marcador e inserimos o novo post no meio
        parts = index_content.split(marker)
        new_index = parts[0] + marker + "\n\n" + item_html + parts[1]
        
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_index)
        print("SUCESSO: Página inicial (index.html) atualizada com o novo post.")
    else:
        print("AVISO: Marcador de inserção não encontrado no index.html. Terá de adicionar o resumo manualmente.")

if __name__ == "__main__":
    # Exemplo de como usar o script (pode ser alterado para aceitar argumentos de linha de comando)
    import sys
    if len(sys.argv) > 3:
        create_post(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Uso: python manage.py \"Título\" \"Resumo\" \"nome-do-ficheiro.txt\"")
