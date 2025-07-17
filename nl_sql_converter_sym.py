# nl_sql_converter_sym.py
# 1. Design and implement a component that takes any natural‐language request and produces an SQL query for a given table 


import os
os.environ["NEUROSYMBOLIC_ENGINE_MODEL"] = "huggingface"
os.environ["HF_MODEL_NAME"] = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
# I had some problems with symai's splash screen, this line is a workaround
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

from symai import Expression
from symai.strategy import contract
from symai.models import LLMDataModel
from pydantic import Field
from transformers import AutoTokenizer, AutoModelForCausalLM
import sqlparse
import re
import sqlglot


# hugging face model setup
MODEL_NAME = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME).to("cpu")
model.eval()

class HuggingFaceEngine:
    def __call__(self, prompt: str) -> str:
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, 
                                 max_new_tokens=150,
                                 eos_token_id=tokenizer.eos_token_id,
                                 pad_token_id=tokenizer.pad_token_id
)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)


# input/output models
class SQLRequest(LLMDataModel):
    request: str = Field(description="Natural language request to convert into SQL")

class SQLResponse(LLMDataModel):
    query: str = Field(description="Syntactically valid SQL query generated from natural language")


# contracted expression
@contract(post_remedy=True, verbose=True)
class GenerateSQL(Expression):
    # the desired SQL dialect can be set here: postgres, mysql, sqlite, tsql etc
    def __init__(self, dialect: str = "sqlite", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialect = dialect.lower()
        # validate the dialect is supported by sqlglot
        if self.dialect not in sqlglot.dialects.Dialect.classes:
            raise ValueError(f"Unsupported SQL dialect: {self.dialect}")
        
        # an example schema to test the SQL generation
        self.schema = {
            "employees": ["id", "name", "role", "salary", "hire_date", "department_id"],
            "departments": ["id", "name", "location", "region_id"],
            "regions": ["id", "name"]
        }

        self.engine = HuggingFaceEngine()
        self._engine = self.engine  
    
    
    @property
    def prompt(self) -> str:
        return (
            f"You are a SQL generation assistant.\n"
            f"Use the {self.dialect.upper()} SQL dialect.\n"
            f"The schema contains related tables with foreign keys.\n"
            f"Schema: {self.schema}\n"
            f"For destructive or deletion requests, assume you are removing rows—not dropping tables.\n"
            f"For creating table requests, first try to create the table using existing tables, i.e. CREATE TABLE AS SELECT and return only one SQL output.\n"
            f"Keep the ORDER BY part clean.\n"
            f"Close all open brackets for example in nested SELECT statements.\n"
            f"Keep the SQL statement as simple, short and concise as possible and avoid unnecessary WHERE clauses.\n"
            f"Use HAVING instead of WHERE for aggregate filtering.\n"
            f"Request: {{request}}\n"
            f"Output a valid SQL query:"
        )

    def forward(self, input: SQLRequest) -> SQLResponse:
        prompt = self.prompt.replace("{request}", input.request)
        raw_sql = self.engine(prompt)
        # for debugging
        # print(f"Generated raw SQL:\n{raw_sql}")
        # extract SQL statement as the response can include the original prompt
        sql = self.extract_sql(raw_sql)
        # for debugging
        # print(f"Generated processed SQL:\n{sql}")

        # validate and transpile SQL to target dialect
        try:
            # this corrects small syntax errors that the LLM might produce
            transpiled_sql = sqlglot.transpile(sql, read=self.dialect, write=self.dialect)
            sql = transpiled_sql[0]  
        except Exception as e:
            return SQLResponse(query=f"-- ERROR: SQL dialect validation failed - {e}")
        
        # fallback validation
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                raise ValueError("Invalid SQL statement.")
        except Exception as e:
            return SQLResponse(query=f"-- ERROR: SQL generation failed - {e}")

        return SQLResponse(query=sql)


    def post(self, output: SQLResponse) -> bool:
        # early rejection for short output (likely malformed or truncated)
        sql = output.query.strip()
        if len(sql) < 20:
            print("Post-validation failed: SQL too short.")
            return False
        
        # extract the first keyword (e.g., SELECT, INSERT, etc.)
        sql_keyword_match = re.match(r"^\s*(\w+)", sql, re.IGNORECASE)
        if not sql_keyword_match:
            return False
        top_keyword = sql_keyword_match.group(1).lower()
        # check for allowed SQL verbs
        allowed_statements = {"select", "insert", "update", "delete", "create", "drop", "alter", "truncate"}
        return top_keyword in allowed_statements
    

    def extract_sql(self, output_text: str) -> str:
        # look for code fences
        match = re.search(r"```sql(.*?)```", output_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        else:
            # splitting after known delimiter
            split_marker = "Output a valid SQL query:"
            if output_text.count(split_marker) == 1:
                candidate = output_text.split(split_marker)[-1].strip()
            # if the LLM outputs multiple SQL statements, take the first one
            elif output_text.count(split_marker) > 1:
                candidate = output_text.split(split_marker)[1].strip()
            else:
                candidate = output_text

            # stop at any common reasoning phrases
            cutoff_phrases = ["Reasoning:", "Explanation:", "Justification:", "Answer:", "Output:", "Request:"]
            for phrase in cutoff_phrases:
                if phrase in candidate:
                    candidate = candidate.split(phrase)[0].strip()

            # clean up and capture consecutive SQL lines
            lines = candidate.splitlines()
            sql_lines = []
            sql_started = False
            for line in lines:
                if line.strip().lower().startswith(("select", "insert", "update", "delete", "create", "drop", "alter", "truncate")):
                    sql_started = True
                if sql_started:
                    sql_lines.append(line)
                sql = "\n".join(sql_lines).strip()
            return sql
    



