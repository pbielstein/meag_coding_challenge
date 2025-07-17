#%% file: test_converter.py


from nl_sql_converter_sym import GenerateSQL, SQLRequest


converter = GenerateSQL()

# select statement
query = SQLRequest(request="List employees hired after 2020")
response = converter(input=query)
print(response.query)

# delete statement
query = SQLRequest(request="Drop all employees hired before 2020")
response = converter(input=query)
print(response.query)

# limit rows
query = SQLRequest(request="show all employees with salary above 70k, limit to 5 rows")
response = converter(input=query)
print(response.query)

# test joins
query = SQLRequest(request="List employee names and their department names")
response = converter(input=query)
print(response.query)

query = SQLRequest(request="List employees based in Munich")
response = converter(input=query)
print(response.query)

# nested joins
query = SQLRequest(request="List employee names and the regions of their departments")
response = converter(input=query)
print(response.query)

# filtering and nested joins
query = SQLRequest(request="Find the average salary of each department for departments with more than five employees.")
response = converter(input=query)
print(response.query)

# test update statement
query = SQLRequest(request="Update the region of all 'Munich' departments to 'Bavaria'.")
response = converter(input=query)
print(response.query)

# testing time arithmetic which is dialect specific
query = SQLRequest(request="Get all employees who joined within the last 90 days.")
response = converter(input=query)
print(response.query)

# full join and ordering
query = SQLRequest(request="Show each employee's name, department name, and the region they work in, ordered by hire date descending.")
response = converter(input=query)
print(response.query)

# creating a new table
query = SQLRequest(request="Create a new table that combines employees and departments, including role and location.")
response = converter(input=query)
print(response.query)

# testing IS NULL logic
query = SQLRequest(request="List departments where no employees are assigned.")
response = converter(input=query)
print(response.query)

# testing count(*)
query = SQLRequest(request="Find the top 3 most populated departments by number of employees.")
response = converter(input=query)
print(response.query)

