"""Testing Agent - Quality Assurance Specialist."""
from typing import Optional
from crewai import Agent
from langchain_openai import ChatOpenAI

from config.settings import Config
from config.prompts import TESTING_PROMPT


class TestingAgent:
    """Specialized agent for writing and running tests."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm or ChatOpenAI(
            model=Config.OPENAI_MODEL,
            api_key=Config.OPENAI_API_KEY,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.OPENAI_MAX_TOKENS
        )
        self.agent: Optional[Agent] = None
    
    def create(self) -> Agent:
        """Create and return the testing agent."""
        self.agent = Agent(
            role='QA Engineer',
            goal='Write comprehensive, reliable tests for Laravel applications ensuring high code quality and coverage',
            backstory=TESTING_PROMPT,
            verbose=Config.AGENT_VERBOSE,
            allow_delegation=False,
            llm=self.llm,
            max_iter=Config.AGENT_MAX_ITERATIONS,
            memory=Config.AGENT_MEMORY,
            tools=[]
        )
        return self.agent
    
    def get_capabilities(self) -> list:
        """Return list of testing capabilities."""
        return [
            'Write PHPUnit feature tests',
            'Write PHPUnit unit tests',
            'Write Pest tests (if project uses Pest)',
            'Test API endpoints',
            'Test form submissions',
            'Test authentication and authorization',
            'Test database operations',
            'Test validation rules',
            'Mock external services',
            'Test file uploads',
            'Test email sending',
            'Test queue jobs',
            'Run full test suite',
            'Generate coverage reports'
        ]
    
    def get_file_patterns(self) -> dict:
        """Return standard test file patterns."""
        return {
            'feature_test': 'tests/Feature/{Name}Test.php',
            'unit_test': 'tests/Unit/{Name}Test.php',
            'pest_test': 'tests/Feature/{Name}Test.php'
        }
    
    def get_test_templates(self) -> dict:
        """Return common test templates."""
        return {
            'api_test': '''<?php

namespace Tests\\Feature;

use Tests\\TestCase;
use Illuminate\\Foundation\\Testing\\RefreshDatabase;

class {ClassName}Test extends TestCase
{
    use RefreshDatabase;

    public function test_can_list_{resource}(): void
    {
        $response = $this->getJson('/api/{resource}');
        
        $response->assertOk();
        $response->assertJsonStructure(['data']);
    }

    public function test_can_create_{resource}(): void
    {
        $data = [
            // Add test data
        ];
        
        $response = $this->postJson('/api/{resource}', $data);
        
        $response->assertCreated();
        $this->assertDatabaseHas('{table}', $data);
    }

    public function test_can_update_{resource}(): void
    {
        $resource = \\App\\Models\\{Model}::factory()->create();
        
        $data = [
            // Add updated data
        ];
        
        $response = $this->putJson("/api/{resource}/{$resource->id}", $data);
        
        $response->assertOk();
        $this->assertDatabaseHas('{table}', $data);
    }

    public function test_can_delete_{resource}(): void
    {
        $resource = \\App\\Models\\{Model}::factory()->create();
        
        $response = $this->deleteJson("/api/{resource}/{$resource->id}");
        
        $response->assertNoContent();
        $this->assertDatabaseMissing('{table}', ['id' => $resource->id]);
    }
}
''',
            'feature_test': '''<?php

namespace Tests\\Feature;

use Tests\\TestCase;
use Illuminate\\Foundation\\Testing\\RefreshDatabase;
use App\\Models\\User;

class {ClassName}Test extends TestCase
{
    use RefreshDatabase;

    public function test_page_requires_authentication(): void
    {
        $response = $this->get('/{route}');
        
        $response->assertRedirect('/login');
    }

    public function test_authenticated_user_can_view_page(): void
    {
        $user = User::factory()->create();
        
        $response = $this->actingAs($user)->get('/{route}');
        
        $response->assertOk();
        $response->assertViewIs('{view}');
    }

    public function test_form_submission_creates_record(): void
    {
        $user = User::factory()->create();
        
        $data = [
            // Add form data
        ];
        
        $response = $this->actingAs($user)->post('/{route}', $data);
        
        $response->assertRedirect();
        $this->assertDatabaseHas('{table}', $data);
    }
}
'''
        }
