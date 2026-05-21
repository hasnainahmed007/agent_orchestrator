"""Interactive CLI interface for Agent Orchestrator."""
import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from agents.roles import AgentRole, AgentInstance
from agents.delegation import DelegatedTask


class CLIInterface:
    """Interactive CLI for managing agents and tasks."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.role_manager = orchestrator.role_manager
        self.delegation = orchestrator.delegation
        self.running = True
    
    def run(self):
        """Run the interactive CLI loop."""
        print("\n" + "=" * 70)
        print("  AGENT ORCHESTRATOR - Interactive CLI")
        print("=" * 70)
        print(f"\nProject: {self.orchestrator.state.state.get('project_name', 'default')}")
        print(f"Team: {len(self.role_manager.instances)} agents | {len(self.role_manager.roles)} roles")
        print("\nType 'help' for available commands.\n")
        
        while self.running:
            try:
                command = input("orchestrator> ").strip()
                if not command:
                    continue
                
                parts = command.split(maxsplit=1)
                cmd = parts[0].lower().replace('-', '_')
                args = parts[1] if len(parts) > 1 else ""
                
                handler = getattr(self, f'cmd_{cmd}', None)
                if handler:
                    handler(args)
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for help.")
                    
            except KeyboardInterrupt:
                print("\n")
                self.cmd_exit("")
            except Exception as e:
                print(f"Error: {e}")
    
    # Team & Agent Management
    # -------------------------------------------------------------------------
    
    def cmd_help(self, args: str):
        """Show help message."""
        print("""
AGENT MANAGEMENT:
  team                  Show full team overview
  agents                List all agent instances
  roles                 List all available roles
  create-agent          Interactive agent creation
  remove-agent <id>     Remove an agent instance
  agent <id>            Show agent details

TASK MANAGEMENT:
  tasks [status]        List tasks (optionally filter by status)
  task <id>             Show task details
  submit                Submit a new task interactively
  process <id>          Process/execute a task
  approve <id>          Approve a pending task
  reject <id>           Reject a pending task

SYSTEM:
  status                Show system status
  skills                List available skills
  templates             List task templates
  template <id>         Show template details
  scan                  Scan project context
  export-team <file>    Export team to YAML
  import-team <file>    Import team from YAML
  dry-run <id>          Preview task without writing files
  exit                  Exit the CLI
""")
    
    def cmd_team(self, args: str):
        """Show team overview."""
        summary = self.role_manager.get_team_summary()
        
        print("\n" + "-" * 70)
        print("TEAM OVERVIEW")
        print("-" * 70)
        print(f"Total Roles: {summary['total_roles']}")
        print(f"Total Agents: {summary['total_instances']}")
        print(f"Available: {summary['available_agents']} | Busy: {summary['busy_agents']}")
        print("\nROLES:")
        for role in summary['roles']:
            print(f"  [{role['hierarchy_level']}] {role['name']} ({role['role_id']})")
            print(f"      Agents: {role['instance_count']}")
        
        print("\nAGENTS:")
        for agent in summary['agents']:
            status_icon = "\U0001F7E2" if agent['status'] == 'idle' else "\U0001F7E1"
            print(f"  {status_icon} {agent['name']} [{agent['role']}] ({agent['instance_id']})")
            print(f"      Tasks completed: {agent['tasks_completed']}")
        print()
    
    def cmd_agents(self, args: str):
        """List all agent instances."""
        instances = self.role_manager.list_instances()
        if not instances:
            print("\nNo agents created yet. Use 'create-agent' to create one.\n")
            return
        
        print("\n" + "-" * 70)
        print("AGENT INSTANCES")
        print("-" * 70)
        
        for inst in instances:
            role = self.role_manager.get_role(inst.role_id)
            role_name = role.name if role else "Unknown"
            
            status_icon = {
                'idle': '\U0001F7E2',
                'busy': '\U0001F7E1',
                'offline': '\U000026AB',
                'error': '\U0001F534'
            }.get(inst.status, '\U000026AB')
            
            print(f"\n{status_icon} {inst.name}")
            print(f"   ID: {inst.instance_id}")
            print(f"   Role: {role_name} ({inst.role_id})")
            print(f"   Status: {inst.status}")
            if inst.current_task_ids:
                print(f"   Current Tasks: {', '.join(inst.current_task_ids)}")
            print(f"   Completed: {inst.total_tasks_completed} | Failed: {inst.total_tasks_failed}")
        print()
    
    def cmd_roles(self, args: str):
        """List all roles."""
        roles = self.role_manager.get_roles_by_hierarchy()
        
        print("\n" + "-" * 70)
        print("AGENT ROLES")
        print("-" * 70)
        
        for role in roles:
            instance_count = len(self.role_manager.get_instances_by_role(role.role_id))
            print(f"\n[{role.hierarchy_level}] {role.name} ({role.role_id})")
            print(f"   Description: {role.description}")
            print(f"   Skills: {', '.join(role.skills)}")
            print(f"   Can delegate to: {', '.join(role.can_delegate_to) or 'None'}")
            print(f"   Reviewed by: {', '.join(role.reviewed_by) or 'None'}")
            print(f"   Approval required: {'Yes' if role.approval_required else 'No'}")
            print(f"   Active agents: {instance_count}")
        print()
    
    def cmd_create_agent(self, args: str):
        """Interactive agent creation."""
        print("\n--- Create New Agent ---")
        
        name = input("Agent name: ").strip()
        if not name:
            print("Name required. Cancelled.")
            return
        
        # Show available roles
        roles = self.role_manager.get_roles_by_hierarchy()
        print("\nAvailable roles:")
        for i, role in enumerate(roles, 1):
            print(f"  {i}. {role.name} ({role.role_id})")
        
        role_input = input("\nSelect role (number or role_id): ").strip()
        
        selected_role = None
        if role_input.isdigit():
            idx = int(role_input) - 1
            if 0 <= idx < len(roles):
                selected_role = roles[idx]
        else:
            selected_role = self.role_manager.get_role(role_input)
        
        if not selected_role:
            print("Invalid role. Cancelled.")
            return
        
        # Skill overrides
        skill_overrides = []
        add_skills = input("Add extra skills? (comma-separated, or empty): ").strip()
        if add_skills:
            skill_overrides = [s.strip() for s in add_skills.split(',') if s.strip()]
        
        try:
            instance = self.orchestrator.create_agent(
                name=name,
                role_id=selected_role.role_id,
                skill_overrides=skill_overrides
            )
            print(f"\nAgent created successfully!")
            print(f"  ID: {instance.instance_id}")
            print(f"  Name: {instance.name}")
            print(f"  Role: {selected_role.name}")
        except Exception as e:
            print(f"Error creating agent: {e}")
    
    def cmd_remove_agent(self, args: str):
        """Remove an agent instance."""
        if not args:
            print("Usage: remove-agent <instance_id>")
            return
        
        instance_id = args.strip()
        instance = self.role_manager.get_instance(instance_id)
        
        if not instance:
            print(f"Agent not found: {instance_id}")
            return
        
        confirm = input(f"Remove agent '{instance.name}'? (yes/no): ").strip().lower()
        if confirm == 'yes':
            self.role_manager.delete_instance(instance_id)
            print(f"Agent {instance_id} removed.")
        else:
            print("Cancelled.")
    
    def cmd_agent(self, args: str):
        """Show agent details."""
        if not args:
            print("Usage: agent <instance_id>")
            return
        
        instance = self.role_manager.get_instance(args.strip())
        if not instance:
            print(f"Agent not found: {args}")
            return
        
        role = self.role_manager.get_role(instance.role_id)
        
        print("\n" + "-" * 70)
        print(f"AGENT: {instance.name}")
        print("-" * 70)
        print(f"ID: {instance.instance_id}")
        print(f"Role: {role.name if role else 'Unknown'} ({instance.role_id})")
        print(f"Status: {instance.status}")
        print(f"Current Tasks: {', '.join(instance.current_task_ids) if instance.current_task_ids else 'None'}")
        print(f"Created: {instance.created_at}")
        print(f"Last Active: {instance.last_active}")
        print(f"\nPerformance:")
        print(f"  Completed: {instance.total_tasks_completed}")
        print(f"  Failed: {instance.total_tasks_failed}")
        print(f"  Avg Time: {instance.average_task_time:.1f}s")
        
        if instance.skill_overrides:
            print(f"\nExtra Skills: {', '.join(instance.skill_overrides)}")
        
        print()
    
    # Task Management
    # -------------------------------------------------------------------------
    
    def cmd_tasks(self, args: str):
        """List tasks."""
        status_filter = args.strip() if args else None
        tasks = self.delegation.list_tasks(status=status_filter)
        
        if not tasks:
            print(f"\nNo tasks found{' with status: ' + status_filter if status_filter else ''}.\n")
            return
        
        print("\n" + "-" * 70)
        print(f"TASKS {f'[{status_filter}]' if status_filter else ''}")
        print("-" * 70)
        
        for task in tasks[:20]:  # Limit to 20
            status_icon = {
                'pending': '\u23F3',
                'assigned': '\U0001F4CB',
                'in_progress': '\U0001F504',
                'delegated': '\U0001F465',
                'under_review': '\U0001F50D',
                'approved': '\u2705',
                'completed': '\u2705',
                'failed': '\u274C',
                'rejected': '\U0001F6AB'
            }.get(task.status, '\u2753')
            
            print(f"\n{status_icon} {task.task_id} - {task.title}")
            print(f"   Status: {task.status}")
            print(f"   Priority: {task.priority}")
            if task.assigned_to:
                agent = self.role_manager.get_instance(task.assigned_to)
                agent_name = agent.name if agent else task.assigned_to
                print(f"   Assigned: {agent_name}")
            if task.subtasks:
                progress = task.get_progress()
                print(f"   Progress: {progress['completed']}/{progress['total']} subtasks")
            print(f"   Created: {task.created_at[:19]}")
        print()
    
    def cmd_task(self, args: str):
        """Show task details."""
        if not args:
            print("Usage: task <task_id>")
            return
        
        task_id = args.strip()
        tree = self.delegation.get_task_tree(task_id)
        
        if not tree:
            print(f"Task not found: {task_id}")
            return
        
        task = tree['task']
        progress = tree['progress']
        
        print("\n" + "-" * 70)
        print(f"TASK: {task['task_id']}")
        print("-" * 70)
        print(f"Title: {task['title']}")
        print(f"Status: {task['status']}")
        print(f"Priority: {task['priority']}")
        print(f"Description: {task['description']}")
        
        if tree['assignee']:
            print(f"\nAssigned to: {tree['assignee']['name']} ({tree['assignee']['role']})")
        
        print(f"\nProgress: {progress['completed']}/{progress['total']}")
        if task['subtasks']:
            print("\nSubtasks:")
            for sub in task['subtasks']:
                status_icon = {
                    'pending': '\u23F3',
                    'assigned': '\U0001F4CB',
                    'in_progress': '\U0001F504',
                    'completed': '\u2705',
                    'failed': '\u274C'
                }.get(sub['status'], '\u2753')
                print(f"  {status_icon} {sub['title']} [{sub['status']}]")
                if sub['assigned_to']:
                    agent = self.role_manager.get_instance(sub['assigned_to'])
                    print(f"      Assigned: {agent.name if agent else sub['assigned_to']}")
        
        if task['result_summary']:
            print(f"\nResult:\n{task['result_summary'][:500]}")
        
        if task['error_message']:
            print(f"\nError: {task['error_message']}")
        
        print()
    
    def cmd_submit(self, args: str):
        """Submit a new task interactively."""
        print("\n--- Submit New Task ---")
        
        title = input("Task title: ").strip()
        if not title:
            print("Title required. Cancelled.")
            return
        
        print("Task description (multi-line, empty line to finish):")
        lines = []
        while True:
            line = input()
            if not line and lines:
                break
            lines.append(line)
        description = "\n".join(lines) or title
        
        print("\nPriority: low, normal, high, critical")
        priority = input("Priority [normal]: ").strip() or "normal"
        
        # Show available agents
        available = self.role_manager.get_available_instances()
        if available:
            print("\nAvailable agents:")
            for i, agent in enumerate(available, 1):
                role = self.role_manager.get_role(agent.role_id)
                print(f"  {i}. {agent.name} ({role.name if role else 'Unknown'})")
            print("  0. Auto-assign")
        
        assign_input = input("\nAssign to (number, agent ID, or 0 for auto): ").strip()
        
        assign_to = None
        if assign_input.isdigit():
            idx = int(assign_input) - 1
            if idx >= 0 and idx < len(available):
                assign_to = available[idx].instance_id
        elif assign_input:
            assign_to = assign_input
        
        try:
            task = asyncio.run(self.orchestrator.submit_task(
                title=title,
                description=description,
                assign_to=assign_to,
                priority=priority
            ))
            print(f"\nTask submitted!")
            print(f"  ID: {task.task_id}")
            print(f"  Status: {task.status}")
            
            if assign_to:
                process = input("Process task now? (yes/no): ").strip().lower()
                if process == 'yes':
                    asyncio.run(self.orchestrator.process_task_with_agent(task.task_id))
                    task = self.delegation.get_task(task.task_id)
                    print(f"  Final Status: {task.status}")
        except Exception as e:
            print(f"Error submitting task: {e}")
    
    def cmd_process(self, args: str):
        """Process/execute a task."""
        if not args:
            print("Usage: process <task_id>")
            return
        
        task_id = args.strip()
        task = self.delegation.get_task(task_id)
        
        if not task:
            print(f"Task not found: {task_id}")
            return
        
        print(f"Processing task {task_id}...")
        try:
            asyncio.run(self.orchestrator.process_task_with_agent(task_id))
            task = self.delegation.get_task(task_id)
            print(f"Task status: {task.status}")
        except Exception as e:
            print(f"Error: {e}")
    
    def cmd_approve(self, args: str):
        """Approve a pending task."""
        if not args:
            print("Usage: approve <task_id>")
            return
        
        task_id = args.strip()
        notes = input("Approval notes (optional): ").strip()
        
        success = asyncio.run(self.orchestrator.approve_task(task_id, "user", notes))
        if success:
            print(f"Task {task_id} approved.")
        else:
            print(f"Failed to approve task {task_id}.")
    
    def cmd_reject(self, args: str):
        """Reject a pending task."""
        if not args:
            print("Usage: reject <task_id>")
            return
        
        task_id = args.strip()
        reason = input("Rejection reason: ").strip()
        
        success = asyncio.run(self.orchestrator.reject_task(task_id, "user", reason))
        if success:
            print(f"Task {task_id} rejected.")
        else:
            print(f"Failed to reject task {task_id}.")
    
    # System Commands
    # -------------------------------------------------------------------------
    
    def cmd_status(self, args: str):
        """Show system status."""
        status = self.orchestrator.get_status()
        
        print("\n" + "-" * 70)
        print("SYSTEM STATUS")
        print("-" * 70)
        print(f"Orchestrator: {status['orchestrator']}")
        print(f"Project: {status['project']} ({status['project_type']})")
        print(f"Skills Loaded: {status['skills_loaded']}")
        print(f"\nTasks:")
        for key, value in status['tasks'].items():
            print(f"  {key}: {value}")
        print()
    
    def cmd_skills(self, args: str):
        """List available skills."""
        skills = self.orchestrator.skill_registry.get_skills_by_category()
        
        print("\n" + "-" * 70)
        print("AVAILABLE SKILLS")
        print("-" * 70)
        
        for category, skill_list in skills.items():
            print(f"\n{category.upper()}:")
            for skill in skill_list:
                print(f"  - {skill.name} ({skill.skill_id}) [{skill.expertise_level}]")
                print(f"    {skill.description}")
        print()
    
    def cmd_scan(self, args: str):
        """Scan project context."""
        print("Scanning project...")
        try:
            self.orchestrator.project_scanner.scan()
            context = self.orchestrator.project_scanner.context
            if context:
                print(f"\nProject: {context.project_name}")
                print(f"Type: {context.project_type}")
                print(f"Language: {context.language}")
                print(f"Framework: {context.framework} {context.framework_version}")
                print(f"Test Framework: {context.test_framework}")
                print(f"Dependencies: {len(context.dependencies)}")
                print(f"Config Files: {', '.join(context.config_files) if context.config_files else 'none'}")
                print("\nStructure:")
                for category, files in context.structure.items():
                    if files:
                        print(f"  {category}: {len(files)} files")
        except Exception as e:
            print(f"Error scanning project: {e}")

    def cmd_templates(self, args: str):
        """List available task templates."""
        from config.task_templates import list_templates
        templates = list_templates()
        if not templates:
            print("No templates available.")
            return

        print("\n" + "-" * 70)
        print("TASK TEMPLATES")
        print("-" * 70)
        for tmpl in templates:
            print(f"\n  [{tmpl['category']}] {tmpl['name']} ({tmpl['id']})")
            print(f"    {tmpl['description']}")
        print("\nUse: template <id> to view full template.")

    def cmd_template(self, args: str):
        """Show a specific task template."""
        if not args:
            print("Usage: template <template_id>")
            print("Use: templates to list available templates.")
            return

        template_id = args.strip()
        from config.task_templates import get_template
        tmpl = get_template(template_id)
        if not tmpl:
            print(f"Template not found: {template_id}")
            return

        print(f"\n{'=' * 70}")
        print(f"TEMPLATE: {tmpl['name']}")
        print(f"{'=' * 70}")
        print(f"Category: {tmpl.get('category', 'general')}")
        print(f"Default Priority: {tmpl.get('default_priority', 'normal')}")
        print(f"\nTemplate Description:\n{tmpl['template']}")
        if tmpl.get('params'):
            print("\nParameters (use `submit-template <id>` to fill these):")
            for k, v in tmpl['params'].items():
                print(f"  {k} = {v}")

    def cmd_dry_run(self, args: str):
        """Preview task execution without modifying files."""
        if not args:
            print("Usage: dry-run <task_id>")
            return

        task_id = args.strip()
        task = self.delegation.get_task(task_id)
        if not task:
            print(f"Task not found: {task_id}")
            return

        print(f"\nDry-running task {task_id}...")
        print("(No files will be modified)")

        from core.dry_run import dry_run_mode
        with dry_run_mode():
            try:
                asyncio.run(self.orchestrator.process_task_with_agent(task_id))
            except Exception as e:
                print(f"Error during dry-run: {e}")

        log = dry_run_mode.get_log()
        if log:
            print(f"\nWould perform {len(log)} actions:")
            for entry in log:
                print(f"  {entry}")
        else:
            print("\nNo actions would be performed.")
        dry_run_mode.clear_log()

    def cmd_export_team(self, args: str):
        """Export team configuration to YAML file."""
        if not args:
            print("Usage: export-team <filepath>")
            return

        filepath = Path(args.strip())
        from core.team_io import export_team
        success = export_team(self.role_manager, filepath)
        if success:
            print(f"Team exported to {filepath}")
        else:
            print(f"Failed to export team to {filepath}")

    def cmd_import_team(self, args: str):
        """Import team configuration from YAML file."""
        if not args:
            print("Usage: import-team <filepath> [--overwrite]")
            return

        parts = args.strip().split()
        filepath = Path(parts[0])
        overwrite = '--overwrite' in parts

        from core.team_io import import_team
        result = import_team(self.role_manager, filepath, overwrite=overwrite)
        print(f"\nImport results:")
        print(f"  Roles created: {len(result['created_roles'])}")
        print(f"  Agents created: {len(result['created_instances'])}")
        print(f"  Skipped: {len(result['skipped_roles']) + len(result['skipped_instances'])}")
        if result['errors']:
            print(f"  Errors: {len(result['errors'])}")
            for err in result['errors']:
                print(f"    - {err}")
        if result['skipped_roles']:
            print(f"\nSkipped roles (use --overwrite to replace):")
            for r in result['skipped_roles']:
                print(f"  - {r}")
        if result['skipped_instances']:
            print(f"Skipped agents (use --overwrite to replace):")
            for i in result['skipped_instances']:
                print(f"  - {i}")
    
    def cmd_exit(self, args: str):
        """Exit the CLI."""
        print("\nShutting down...")
        self.running = False
