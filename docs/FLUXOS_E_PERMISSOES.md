# Documentação de Fluxos, Multi-Tenant e Matriz Granular de Permissões

## 1. Estrutura de Domínio & Hierarquia de Usuários

### Nível 1: Admin System
- **Função**: Gerenciar o cadastro de **User Clients (Gestores de Clínicas)** e habilitar quais **Integradores** (Unimed Goiânia, IPASGO, Bradesco, Evoluir, ABA CLMF, etc.) cada cliente tem direito de utilizar.
- **Tabela de Habilitação**: `public.user_integradores` (`user_id`, `id_integrador`).
- **Mapeamento de Convênios**: Relaciona a tabela `public.convenios` com os respectivos integradores cadastrados no sistema.

### Nível 2: Gestor da Clínica (Client)
- **Função**: Administrar as credenciais da clínica (`user_convenios`), cadastrar sub-usuários (Operadores: Recepcionistas, Faturistas, Supervisores) e gerenciar a matriz granular de permissões de cada operador.
- **Herança**: Todos os sub-usuários criados pelo Gestor herdam o `parent_user_id` do Gestor.

### Nível 3: Sub-usuários / Operadores (ex: `DGR2026`)
- **Resolução Multi-tenant**: Ao realizar qualquer consulta (`/agendamentos`, `/carteirinhas`, `/guias`, `/faturamento`), o backend resolve:
  $$\text{effective\_user\_id} = \begin{cases} \text{user.parent\_user\_id} & \text{se sub-usuário} \\ \text{user.id} & \text{se gestor/admin} \end{cases}$$
- **Resultado**: Sub-usuários visualizam e operam 100% dos dados da clínica do seu Gestor sem perda de contexto ou contaminação entre clínicas.

---

## 2. Matriz Granular de Permissões por Módulo e Botões de Ação

Cada operador possui uma estrutura de permissões armazenada em `public.users.permissoes` (JSONB) que especifica granularmente o acesso aos módulos e botões de ação:

### Exemplo de Estrutura JSONB:
```json
{
  "workflow_faturamento": {
    "visualizar": true,
    "filtrar": true,
    "sincronizar": true,
    "executar_faturamento": false,
    "alterar_status": false
  },
  "agendamentos": {
    "visualizar": true,
    "filtrar": true,
    "sincronizar": true,
    "editar": true
  },
  "guias": {
    "visualizar": true,
    "solicitar": false,
    "imprimir": true
  },
  "faturamento_lotes": {
    "visualizar": false,
    "criar": false,
    "enviar": false
  }
}
```

### Perfis Padrão:
1. **Agendamento**:
   - Módulos: Agendamentos e Consulta de Guias.
   - Restrições: Pode visualizar o Workflow de Faturamento e sincronizar agendamentos, mas **não pode executar ações de faturamento**.
2. **Faturamento**:
   - Módulos: Workflow Faturamento, Lotes e Conciliação.
   - Permissões: Transmitir lotes, conciliar dados e faturar.
3. **Supervisor**:
   - Módulos: Acesso completo com permissão de edição em todos os fluxos da clínica.

---

## 3. Desacoplamento do Schema `Integrador` (`public` vs `worker`)

- **`public.integradores`**: Cadastro master dos integradores e convênios no sistema principal.
- **`public.integrador_operacoes`**:
  - `id`: Primary Key.
  - `id_integrador`: Foreign Key para `public.integradores.id_integrador`.
  - `id_integrador_worker`: Referência lógica ao código do integrador no schema `worker` (apenas valor numérico, **sem restrição de Foreign Key cruzada entre schemas**).
  - `id_convenio`: Foreign Key para `public.convenios.id_convenio`.
- **`worker.integradores` & `worker.integrador_operacoes`**: Execução isolada de scrapers e workers locais sem acoplamento direto de concorrência/lock no schema public.

---
*Documentação atualizada em 2026-08-12 por Antigravity AI.*
