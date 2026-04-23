"""Agent tools for file operations and command execution."""
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple


class AgentTools:
    """Tools available to agents for interacting with the project."""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.files_touched: List[str] = []
    
    def read_file(self, file_path: str) -> str:
        """Read contents of a file.
        
        Args:
            file_path: Relative path from project root
            
        Returns:
            File contents or error message
        """
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return f"[ERROR] File not found: {file_path}"
            
            content = full_path.read_text(encoding='utf-8')
            return content
        except Exception as e:
            return f"[ERROR] Could not read file: {e}"
    
    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file (creates if not exists).
        
        Args:
            file_path: Relative path from project root
            content: Content to write
            
        Returns:
            Success or error message
        """
        try:
            full_path = self._resolve_path(file_path)
            
            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content, encoding='utf-8')
            
            # Track file
            rel_path = str(full_path.relative_to(self.project_path)).replace('\\', '/')
            if rel_path not in self.files_touched:
                self.files_touched.append(rel_path)
            
            return f"[SUCCESS] Created file: {file_path}"
        except Exception as e:
            return f"[ERROR] Could not write file: {e}"
    
    def edit_file(self, file_path: str, old_string: str, new_string: str) -> str:
        """Edit a specific part of a file.
        
        Args:
            file_path: Relative path from project root
            old_string: String to find and replace
            new_string: String to replace with
            
        Returns:
            Success or error message
        """
        try:
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                return f"[ERROR] File not found: {file_path}"
            
            content = full_path.read_text(encoding='utf-8')
            
            if old_string not in content:
                return f"[ERROR] Could not find text to replace in {file_path}"
            
            new_content = content.replace(old_string, new_string, 1)
            full_path.write_text(new_content, encoding='utf-8')
            
            # Track file
            rel_path = str(full_path.relative_to(self.project_path)).replace('\\', '/')
            if rel_path not in self.files_touched:
                self.files_touched.append(rel_path)
            
            return f"[SUCCESS] Modified file: {file_path}"
        except Exception as e:
            return f"[ERROR] Could not edit file: {e}"
    
    def search_files(self, pattern: str, directory: str = "") -> List[str]:
        """Search for files matching pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.php", "*Controller.php")
            directory: Subdirectory to search in
            
        Returns:
            List of matching file paths
        """
        try:
            search_dir = self.project_path / directory if directory else self.project_path
            matches = list(search_dir.rglob(pattern))
            
            return [
                str(m.relative_to(self.project_path)).replace('\\', '/')
                for m in matches if m.is_file()
            ][:20]  # Limit to 20 results
        except Exception as e:
            return [f"[ERROR] Search failed: {e}"]
    
    def list_directory(self, directory: str = "") -> str:
        """List contents of a directory.
        
        Args:
            directory: Relative directory path
            
        Returns:
            Directory listing as string
        """
        try:
            dir_path = self._resolve_path(directory) if directory else self.project_path
            
            if not dir_path.exists():
                return f"[ERROR] Directory not found: {directory}"
            
            items = []
            for item in sorted(dir_path.iterdir()):
                item_type = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{item_type} {item.name}")
            
            return "\n".join(items)
        except Exception as e:
            return f"[ERROR] Could not list directory: {e}"
    
    def run_command(self, command: str) -> str:
        """Run a shell command in the project directory.
        
        Args:
            command: Command to run (e.g., "php artisan migrate")
            
        Returns:
            Command output
        """
        import subprocess
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_path)
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr
            
            if result.returncode != 0:
                output = f"[EXIT CODE: {result.returncode}]\n" + output
            
            return output[:5000]  # Limit output length
        except subprocess.TimeoutExpired:
            return "[ERROR] Command timed out after 60 seconds"
        except Exception as e:
            return f"[ERROR] Command failed: {e}"
    
    def get_project_structure(self) -> str:
        """Get a summary of project structure.
        
        Returns:
            Project structure as string
        """
        lines = ["Project Structure:"]
        
        # Key directories
        key_dirs = ['app', 'resources', 'routes', 'database', 'tests']
        for dir_name in key_dirs:
            dir_path = self.project_path / dir_name
            if dir_path.exists():
                lines.append(f"\n{dir_name}/")
                for item in sorted(dir_path.iterdir())[:10]:
                    lines.append(f"  {item.name}/" if item.is_dir() else f"  {item.name}")
        
        return "\n".join(lines)
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a relative path to absolute path.
        
        Args:
            file_path: Relative path
            
        Returns:
            Absolute Path object
        """
        # Normalize path separators
        file_path = file_path.replace('/', os.sep).replace('\\', os.sep)
        
        # Security: Prevent directory traversal
        full_path = (self.project_path / file_path).resolve()
        
        if not str(full_path).startswith(str(self.project_path)):
            raise ValueError(f"Access denied: {file_path} is outside project directory")
        
        return full_path
    
    def get_touched_files(self) -> List[str]:
        """Get list of files touched during this session.
        
        Returns:
            List of file paths
        """
        return self.files_touched.copy()
    
    def clear_touched_files(self):
        """Clear the list of touched files."""
        self.files_touched = []


def create_tools(project_path: Path) -> AgentTools:
    """Factory function to create tools instance."""
    return AgentTools(project_path)