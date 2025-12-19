from protos.person_pb2 import Person

print(Person)

person = Person()
person.name = "Alice"
person.id = 123
person.email = "alice@example.com"

print(person)

serialized_person = person.SerializeToString()
print(serialized_person)

new_person = Person()
new_person.ParseFromString(serialized_person)
print(new_person)
