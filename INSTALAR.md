# Instalar rclone + Google Drive (LGM)

O rclone é o programa que copia/sincroniza arquivos entre o PC e o Google Drive pela linha de comando — base para as automações de backup e organização de processos.

## Opção 1 — Automática (recomendada)

1. Clique com o botão direito em `Instalar_Rclone_Drive.ps1` → **Executar com o PowerShell**.
   - Se o Windows bloquear: abra o PowerShell e rode
     `powershell -ExecutionPolicy Bypass -File "C:\caminho\Instalar_Rclone_Drive.ps1"`
2. O navegador abre → entre com a **conta Google do escritório** → **Permitir**.
3. Ao final aparecem as pastas do Drive. Pronto.

O script faz as 3 etapas sozinho e pode ser rodado de novo sem problema (pula o que já está feito).

## Opção 2 — Manual (os 3 comandos)

```powershell
winget install Rclone.Rclone     # instala
rclone config                    # conecta o Drive (respostas abaixo)
rclone lsd gdrive_lgm:           # testa
```

> Depois do `winget install`, **feche e abra o PowerShell** antes do `rclone config` (senão aparece "rclone não é reconhecido").

### Respostas do `rclone config`

| Pergunta que aparece | Digite |
|---|---|
| `n) New remote` / `e/n/d/r/c/s/q>` | `n` |
| `name>` | `gdrive_lgm` |
| `Storage>` | `drive` |
| `client_id>` | *Enter (vazio)* |
| `client_secret>` | *Enter (vazio)* |
| `scope>` | `1` (acesso total) |
| `service_account_file>` | *Enter (vazio)* |
| `Edit advanced config?` | `n` |
| `Use web browser to automatically authenticate?` | `y` → navegador abre → login → **Permitir** |
| `Configure this as a Shared Drive (Team Drive)?` | `n` *(ver observação abaixo)* |
| `Keep this "gdrive_lgm" remote?` | `y` |
| menu final | `q` (sair) |

**Drive compartilhado:** se os arquivos do escritório ficam em um *Drive compartilhado* (não em "Meu Drive"), responda `y` nessa pergunta e escolha o número do drive na lista.

### Teste

`rclone lsd gdrive_lgm:` deve listar as pastas da raiz do Drive. Se listar, está funcionando.

## Problemas comuns

| Sintoma | Solução |
|---|---|
| `rclone não é reconhecido` | Feche e abra o PowerShell. Persistindo, rode o script da Opção 1. |
| `winget não é reconhecido` | Use o script da Opção 1 (ele baixa direto do site oficial). |
| Navegador não abriu | Copie o link `http://127.0.0.1:53682/auth?...` exibido no terminal e cole no navegador. |
| Google mostra "Acesso bloqueado" / "app não verificado" | Conta Google Workspace com bloqueio de apps de terceiros: o administrador do Workspace precisa liberar o app "rclone" (Admin Console → Segurança → Controles de API). |
| `lsd` deu erro de token / `invalid_grant` | `rclone config reconnect gdrive_lgm:` e faça o login de novo. |
| Lista vazia | Os arquivos podem estar em *Drive compartilhado*: refaça com `rclone config` respondendo `y` na pergunta do Shared Drive. |

## Segurança (LGPD)

- A chave de acesso ao Drive fica em `%APPDATA%\rclone\rclone.conf`. **Nunca** envie esse arquivo, nem coloque no GitHub (já está bloqueado no `.gitignore`).
- Se o PC for perdido/trocado: revogue o acesso em <https://myaccount.google.com/permissions> (item "rclone").
