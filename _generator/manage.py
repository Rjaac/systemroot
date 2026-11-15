import os
import datetime
import subprocess
import sys
import unicodedata
import re
import shutil
import html

# --- CONFIGURAÇÕES ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BASE_DIR, 'posts')
PUBLISHED_TXT_DIR = os.path.join(POSTS_DIR, 'text_files', 'published')
TEMPLATES_DIR = os.path.join(BASE_DIR, '_generator', 'templates')
TXT_TEMPLATES_DIR = os.path.join(BASE_DIR, '_generator', 'txt_templates')
ACTIVE_DRAFT_FILE = os.path.join(BASE_DIR, '_generator', 'active_draft.txt')
LOG_FILE = os.path.join(BASE_DIR, '_generator', 'published_log.txt')

INDEX_FILE = os.path.join(BASE_DIR, 'index.html')
PHOTOS_FILE = os.path.join(BASE_DIR, 'photos.html')
BOOKS_FILE = os.path.join(BASE_DIR, 'books.html')
CODE_FILE = os.path.join(BASE_DIR, 'code.html')


def slugify(text):
    """
    Converte um título num nome de ficheiro limpo (ASCII, minúsculas, apenas letras, números e hífens).
    """
    normalized = unicodedata.normalize('NFKD', text)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
    return slug or 'transmission'


def git_sync(commit_prefix, title):
    """
    Automatiza o processo de salvar no GitHub ('git add', 'git commit' e 'git push').
    """
    print("\n--- INICIALIZANDO SINCRONIZAÇÃO GIT ---")
    try:
        subprocess.run(["git", "add", "."], check=True, cwd=BASE_DIR)
        commit_msg = f"{commit_prefix}: {title}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True, cwd=BASE_DIR)
        subprocess.run(["git", "push", "origin", "main"], check=True, cwd=BASE_DIR)
        print("SUCESSO: Blog sincronizado com o GitHub e Netlify!")
    except subprocess.CalledProcessError:
        print("ERRO no Git: Ocorreu um problema ao sincronizar.")
    except Exception:
        print("AVISO: Git não configurado.")


def inject_into_page(page_path, marker, item_html):
    """
    Insere um novo bloco HTML logo abaixo do marcador indicado na página alvo.
    """
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if marker in content:
        parts = content.split(marker, 1)
        new_content = parts[0] + marker + "\n\n" + item_html + parts[1]
        with open(page_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"SUCESSO: Página '{os.path.basename(page_path)}' atualizada.")
        return True
    else:
        print(f"AVISO: Marcador '{marker}' não encontrado em {os.path.basename(page_path)}.")
        return False


def archive_and_log(content_type, title, slug, source_txt_path=None, raw_text=None):
    """
    Guarda uma cópia do ficheiro .txt publicado em posts/text_files/published/
    e regista a publicação em _generator/published_log.txt.
    """
    os.makedirs(PUBLISHED_TXT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_prefix = datetime.datetime.now().strftime("%Y-%m-%d")
    archived_name = f"{date_prefix}_{content_type}_{slug}.txt"
    archived_path = os.path.join(PUBLISHED_TXT_DIR, archived_name)

    if source_txt_path and os.path.exists(source_txt_path):
        shutil.copy2(source_txt_path, archived_path)
    elif raw_text is not None:
        with open(archived_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)

    log_entry = f"[{timestamp}] TYPE={content_type.upper()} | TITLE=\"{title}\" | ARCHIVE=posts/text_files/published/{archived_name}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

    print(f"ARQUIVO: Guardado em 'posts/text_files/published/{archived_name}'")


def parse_template_file(filepath):
    """
    Lê um ficheiro .txt com cabeçalhos (CHAVE: valor) separados do corpo por '---'.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        raw = f.read()

    if '---' in raw:
        header_part, body_part = raw.split('---', 1)
    else:
        header_part, body_part = "", raw

    headers = {}
    for line in header_part.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip().upper()] = v.strip()

    return headers, body_part.strip(), raw


def format_paragraphs(body_text):
    """
    Converte linhas de texto em parágrafos <p>, ignorando linhas vazias ou marcadores repetidos.
    """
    lines = [
        line.strip() for line in body_text.splitlines()
        if line.strip() and line.strip() != '// TRANSMISSION_COMPLETE //'
    ]
    return "\n                ".join([f"<p>{line}</p>" for line in lines])


def format_code_body(body_text):
    """
    Converte texto que pode conter blocos [CODE]...[/CODE] em HTML (<p> e <pre class="code-snippet">).
    """
    pattern = re.compile(r'\[CODE\](.*?)\[/CODE\]', re.DOTALL | re.IGNORECASE)
    parts = []
    last_idx = 0

    for match in pattern.finditer(body_text):
        before = body_text[last_idx:match.start()].strip()
        if before:
            for line in before.splitlines():
                if line.strip():
                    parts.append(f"<p>{line.strip()}</p>")
        code_block = html.escape(match.group(1).strip('\r\n'))
        if code_block:
            parts.append(f'<pre class="code-snippet">\n{code_block}\n            </pre>')
        last_idx = match.end()

    remaining = body_text[last_idx:].strip()
    if remaining:
        for line in remaining.splitlines():
            if line.strip():
                parts.append(f"<p>{line.strip()}</p>")

    return "\n            ".join(parts)


def publish_post(title, summary, body_text, source_path=None, raw_text=None):
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    filename = slugify(title)
    formatted_content = format_paragraphs(body_text)

    with open(os.path.join(TEMPLATES_DIR, 'post_template.html'), 'r', encoding='utf-8') as f:
        post_html = f.read()

    post_html = post_html.replace('{{TITLE}}', title)
    post_html = post_html.replace('{{DATE}}', date_str)
    post_html = post_html.replace('{{CONTENT}}', formatted_content)

    new_post_path = os.path.join(POSTS_DIR, f"{filename}.html")
    with open(new_post_path, 'w', encoding='utf-8') as f:
        f.write(post_html)
    print(f"SUCESSO: Post criado em 'posts/{filename}.html'")

    with open(os.path.join(TEMPLATES_DIR, 'index_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()

    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{SUMMARY}}', summary)
    item_html = item_html.replace('{{FILENAME}}', filename)
    item_html = item_html.replace('{{DATE}}', date_str)

    inject_into_page(INDEX_FILE, '<h2>LATEST TRANSMISSION_</h2>', item_html)
    archive_and_log('post', title, filename, source_path, raw_text)
    git_sync('Post', title)


def publish_photo(title, image_path, body_text, source_path=None, raw_text=None):
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    slug = slugify(title)
    if image_path and not image_path.startswith(('img/', 'http://', 'https://', '/')):
        image_path = f"img/{image_path}"

    formatted_content = format_paragraphs(body_text)

    with open(os.path.join(TEMPLATES_DIR, 'photo_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()

    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{DATE}}', date_str)
    item_html = item_html.replace('{{IMAGE}}', image_path)
    item_html = item_html.replace('{{CONTENT}}', formatted_content)

    inject_into_page(PHOTOS_FILE, '<!-- LATEST_PHOTO_MARKER -->', item_html)
    archive_and_log('photo', title, slug, source_path, raw_text)
    git_sync('Photo', title)


def publish_book(title, status, link, image_path, body_text, source_path=None, raw_text=None):
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    slug = slugify(title)

    image_block = ""
    if image_path:
        if not image_path.startswith(('img/', 'http://', 'https://', '/')):
            image_path = f"img/{image_path}"
        image_block = f'            <div class="photo-item" style="margin-bottom: 1rem;">\n                <img src="{image_path}" alt="{title}">\n            </div>'

    link_block = ""
    if link and link not in ('https://', 'http://'):
        link_block = f'            <p><a href="{link}" target="_blank" rel="noopener noreferrer" class="back-link">[ &gt;&gt; ACEDER / COMPRAR PUBLICAÇÃO ]</a></p>'

    formatted_content = format_paragraphs(body_text)

    with open(os.path.join(TEMPLATES_DIR, 'book_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()

    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{DATE}}', date_str)
    item_html = item_html.replace('{{STATUS}}', status or 'Disponível')
    item_html = item_html.replace('{{IMAGE_BLOCK}}', image_block)
    item_html = item_html.replace('{{CONTENT}}', formatted_content)
    item_html = item_html.replace('{{LINK_BLOCK}}', link_block)

    inject_into_page(BOOKS_FILE, '<!-- LATEST_BOOK_MARKER -->', item_html)
    archive_and_log('book', title, slug, source_path, raw_text)
    git_sync('Book', title)


def publish_code(title, description, body_text, source_path=None, raw_text=None):
    date_str = datetime.datetime.now().strftime("%Y.%m.%d")
    slug = slugify(title)
    formatted_content = format_code_body(body_text)

    with open(os.path.join(TEMPLATES_DIR, 'code_item_template.html'), 'r', encoding='utf-8') as f:
        item_html = f.read()

    item_html = item_html.replace('{{TITLE}}', title)
    item_html = item_html.replace('{{DATE}}', date_str)
    item_html = item_html.replace('{{DESCRIPTION}}', description)
    item_html = item_html.replace('{{CONTENT}}', formatted_content)

    inject_into_page(CODE_FILE, '<!-- LATEST_CODE_MARKER -->', item_html)
    archive_and_log('code', title, slug, source_path, raw_text)
    git_sync('Code', title)


def interactive_wizard(content_type=None):
    """
    Fluxo interativo: escolhe o tipo (se não foi passado), abre o modelo no Notepad,
    lê os dados quando o Notepad fecha e publica após confirmação.
    """
    valid_types = {'1': 'post', '2': 'photo', '3': 'book', '4': 'code'}

    if not content_type:
        print("==================================================")
        print("   SYSTEM_ROOT :: TERMINAL PUBLISHING PROTOCOL    ")
        print("==================================================")
        print("  [1] post   -> Novo Post no Blog (index.html)")
        print("  [2] photo  -> Nova Captura Visual (photos.html)")
        print("  [3] book   -> Nova Publicação / Livro (books.html)")
        print("  [4] code   -> Novo Projeto / Código (code.html)")
        print("  [L] log    -> Ver histórico de publicações")
        print("  [Q] sair   -> Cancelar")
        print("==================================================")
        choice = input(">> Seleciona a opção: ").strip().lower()
        if choice in ('q', 'sair', ''):
            print("Operação cancelada.")
            return
        if choice in ('l', 'log'):
            show_log()
            return
        content_type = valid_types.get(choice, choice)

    content_type = content_type.lower().strip()
    if content_type == 'log':
        show_log()
        return

    if content_type not in ('post', 'photo', 'book', 'code'):
        print(f"ERRO: Tipo '{content_type}' inválido. Usa: post, photo, book, code ou log.")
        return

    template_src = os.path.join(TXT_TEMPLATES_DIR, f"{content_type}.txt")
    if os.path.exists(ACTIVE_DRAFT_FILE):
        existing_headers, _, _ = parse_template_file(ACTIVE_DRAFT_FILE)
        if existing_headers.get('TITLE', '').strip():
            reuse = input("\n>> Existe um rascunho anterior por publicar. Queres continuar a editá-lo? (S/N): ").strip().lower()
            if reuse not in ('s', 'sim', 'y', 'yes'):
                shutil.copy2(template_src, ACTIVE_DRAFT_FILE)
        else:
            shutil.copy2(template_src, ACTIVE_DRAFT_FILE)
    else:
        shutil.copy2(template_src, ACTIVE_DRAFT_FILE)

    print(f"\n>> A abrir o Notepad com o ficheiro: {ACTIVE_DRAFT_FILE}")
    print(">> 1. Escreve/cola o teu conteúdo no Notepad")
    print(">> 2. Guarda no Notepad (Ctrl+S)")
    subprocess.Popen(["notepad.exe", ACTIVE_DRAFT_FILE])

    while True:
        choice = input("\n>> Depois de fazeres Ctrl+S no Notepad, prime [ENTER] aqui para avançar (ou 'q' para cancelar): ").strip().lower()
        if choice in ('q', 'sair', 'cancelar'):
            print("Operação cancelada.")
            return

        if not os.path.exists(ACTIVE_DRAFT_FILE):
            print("AVISO: Rascunho não encontrado.")
            return

        headers, body, raw_text = parse_template_file(ACTIVE_DRAFT_FILE)
        title = headers.get('TITLE', '').strip()

        if title:
            break
        print("\n[AVISO] O campo 'TITLE:' ainda aparece vazio no ficheiro!")
        print("Certifica-te de que preencheste 'TITLE: ...' no separador certo do Notepad e carregaste em Ctrl+S.")

    print("\n--------------------------------------------------")
    print(f"  TIPO:   {content_type.upper()}")
    print(f"  TÍTULO: {title}")
    if content_type == 'post':
        print(f"  RESUMO: {headers.get('SUMMARY', '')}")
    elif content_type == 'photo':
        print(f"  IMAGEM: {headers.get('IMAGE', '')}")
    elif content_type == 'book':
        print(f"  STATUS: {headers.get('STATUS', 'Disponível')}")
        print(f"  LINK:   {headers.get('LINK', '')}")
    elif content_type == 'code':
        print(f"  DESC:   {headers.get('DESCRIPTION', '')}")
    print("--------------------------------------------------")

    confirm = input(">> Confirmar publicação e enviar para o Netlify? (S/N): ").strip().lower()
    if confirm not in ('s', 'sim', 'y', 'yes'):
        print(f"Publicação adiada. O teu rascunho continua guardado em: {ACTIVE_DRAFT_FILE}")
        return

    if content_type == 'post':
        publish_post(title, headers.get('SUMMARY', ''), body, ACTIVE_DRAFT_FILE, raw_text)
    elif content_type == 'photo':
        publish_photo(title, headers.get('IMAGE', ''), body, ACTIVE_DRAFT_FILE, raw_text)
    elif content_type == 'book':
        publish_book(
            title,
            headers.get('STATUS', 'Disponível'),
            headers.get('LINK', ''),
            headers.get('IMAGE', ''),
            body,
            ACTIVE_DRAFT_FILE,
            raw_text,
        )
    elif content_type == 'code':
        publish_code(title, headers.get('DESCRIPTION', ''), body, ACTIVE_DRAFT_FILE, raw_text)

    if os.path.exists(ACTIVE_DRAFT_FILE):
        os.remove(ACTIVE_DRAFT_FILE)


def show_log():
    print("\n--- HISTÓRICO DE PUBLICAÇÕES (SYSTEM_ROOT) ---")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("Ainda não existem entradas registadas no log.")


def create_post(title, summary, content_file):
    """
    Modo clássico por linha de comandos: python manage.py "Título" "Resumo" "ficheiro.txt"
    """
    if os.path.exists(content_file):
        txt_path = content_file
    else:
        txt_path = os.path.join(POSTS_DIR, 'text_files', content_file)

    if not os.path.exists(txt_path):
        print(f"ERRO: Ficheiro não encontrado em: {txt_path}")
        return

    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()

    publish_post(title, summary, raw_content, source_path=txt_path, raw_text=raw_content)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        interactive_wizard()
    elif len(sys.argv) == 2:
        interactive_wizard(sys.argv[1])
    elif len(sys.argv) > 3:
        create_post(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Uso:")
        print("  PUBLISH                      -> Menu interativo (abre o Notepad)")
        print("  PUBLISH post|photo|book|code -> Abre diretamente o modelo no Notepad")
        print("  PUBLISH log                  -> Mostra o histórico de publicações")
        print("  python manage.py \"Título\" \"Resumo\" \"ficheiro.txt\"")
