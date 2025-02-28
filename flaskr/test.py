file = open("flaskr/vegsystem.txt", "r", encoding="utf-8")
vegsystem = [tuple([None if i == "0" else i for i in line.replace("\n","").split(", ")]) for line in file.readlines()]
print(vegsystem)