import os
import datetime
import subprocess
import sys

# --- CONFIGURAÇÕES ---
# Onde estão os ficheiros do blog
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')
TEMPLATES_DIR = os.path.join(BASE_DIR, '_generator', 'templates')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')

def git_sync(title):
    """
    Esta função automatiza o processo de salvar no GitHub.
    Ela executa os comandos 'git add', 'git commit' e 'git push'.
    """
    print("\n--- INICIALIZANDO SINCRONIZAÇÃO GIT ---")
    try:
        # 1. Adicionar todas as alterações
        subprocess.run(["git", "add", "."], check=True, cwd=BASE_DIR)
        
        # 2. Criar o commit
        commit_msg = f"Post: {title}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=BASE_DIR)
        
        # 3. Enviar para o GitHub
        subprocess.run(["git", "push", "origin", "main"], check=True, cwd=BASE_DIR)
        
        print("SUCESSO: Blog sincronizado com o GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"ERRO no Git: Ocorreu um problema ao sincronizar.")
    except Exception as e:
        print(f"AVISO: Git não configurado.")

def update_index(title, summary, filename, date_str):
    """
    Esta função insere o resumo do novo post no index.html.
    """
    with open(os.path.join(TEMPLATES_DIR, 'index_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()
    
    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{SUMMARY}}', summary)
    item_html = item_html.replace('{{FILENAME}}', filename)
    item_html = item_html.replace('{{DATE}}', date_str)

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        index_content = f.read()

    marker = '<h2>LATEST TRANSMISSION_</h2>'
    if marker in index_content:
        parts = index_content.split(marker)
        new_index = parts[0] + marker + "\n\n" + item_html + parts[1]
        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            f.write(new_index)
        print("SUCESSO: Página inicial (index.html) atualizada.")
    else:
        print("AVISO: Marcador não encontrado no index.html.")

def create_post(title, summary, content_file):
    """
    Função principal para criar o post.
    """
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    filename = title.lower().replace(" ", "-").replace(":", "").replace("_", "-").replace("'", "").replace(",", "")
    
    if os.path.exists(content_file):
        txt_path = content_file
    else:
        txt_path = os.path.join(POSTS_DIR, 'text_files', content_file)
    
    if not os.path.exists(txt_path):
        print(f"ERRO: Ficheiro não encontrado em: {txt_path}")
        return

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()
        formatted_content = "".join([f"<p>{line}</p>" for line in raw_content.split('\n') if line.strip()])

    with open(os.path.join(TEMPLATES_DIR, 'post_template.html'), 'r', encoding='utf-8') as f:
        post_html = f.read()
    
    post_html = post_html.replace('{{TITLE}}', title)
    post_html = post_html.replace('{{DATE}}', date_str)
    post_html = post_html.replace('{{CONTENT}}', formatted_content)

    new_post_path = os.path.join(POSTS_DIR, f"{filename}.html")
    with open(new_post_path, 'w', encoding='utf-8') as f:
        f.write(post_html)
    print(f"SUCESSO: Post criado em '{new_post_path}'")

    update_index(title, summary, filename, date_str)
    git_sync(title)

if __name__ == "__main__":
    if len(sys.argv) > 3:
        create_post(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Uso: python manage.py \"Título\" \"Resumo\" \"nome-do-ficheiro.txt\"")
