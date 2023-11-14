from flask import Flask, request, render_template, redirect, url_for, jsonify,send_file,make_response,Response
import pdfplumber
from pymongo import MongoClient
from gridfs import GridFS
from bson import ObjectId
import io
import re

app=Flask(__name__)

client = MongoClient('mongodb+srv://gaja:gaja123@cluster0.jdoybcv.mongodb.net/gameproject')
db = client["pdf_data"]
fs = GridFS(db)

# @app.route("/")
# def get_all_data():
#     all_data_cursor = fs.find({})
#     all_data = list(all_data_cursor)
#     all_data_cursor.close()  # Close the cursor explicitly
#     processed_data = [{"filename": item.filename, "text": item.metadata["text"]} for item in all_data]
#     return render_template('home.html', data=processed_data)

# invoice_number_pattern = re.compile(r'(?i)invoice\s*number\s*:\s*([^\s,]+)')

@app.route("/")
def get_all_data():
    all_data_cursor = fs.find({})
    all_data = list(all_data_cursor)
    all_data_cursor.close()

    processed_data = []
    for idx, item in enumerate(all_data):
        upload_date = item.uploadDate.strftime("%Y-%m-%d %H:%M:%S")
        # invoice_number = item.metadata.get("INVOICE#", item.metadata.get("Invoice Number", "N/A"))
        # Extract invoice number using regular expression
        text = item.metadata.get("text", "")
        print("i am here pdftext",text)
        # Try to match patterns resembling invoice numbers
        invoice_number_match = re.search(r'\b(?:INVOICE#|Invoice Number)\s*:\s*([^\n\r]+)\b', text, re.IGNORECASE)
        # If no match is found, use a more generic pattern
        if not invoice_number_match:
            invoice_number_match = re.search(r'\b(\w{3,}[-/]\d{7,})\b', text)
        invoice_number = invoice_number_match.group(1) if invoice_number_match else "N/A"
        # print("invoice is",invoice_number)
        # invoice_number = item.metadata.get("INVOICE#", "N/A")
        uploaded_from = "Web" 

        data_entry = {
            "no": idx + 1,
            "filename": item.filename,
            "upload_date": upload_date,
            "invoice_number": invoice_number,
            "uploaded_from": uploaded_from,
            "text": item.metadata["text"],
            "pdf_id": str(item._id) 
        }
        processed_data.append(data_entry)

    return render_template('home.html', data=processed_data)

# @app.route("/viewinvoice/<pdf_id>")
# def view_invoice(pdf_id):
#     pdf_data = fs.find_one({"_id": ObjectId(pdf_id)})
#     return send_file(pdf_data, as_attachment=True, download_name=pdf_data.filename)

# Route to view an uploaded PDF
@app.route("/viewinvoice/<pdf_id>")
def view_invoice(pdf_id):
    pdf_data = fs.find_one({"_id": ObjectId(pdf_id)})
    # print(pdf_data)

    if pdf_data:
        pdf_content = pdf_data.read()
        response = Response(pdf_content, content_type='application/pdf')
        response.headers["Content-Disposition"] = f"inline; filename={pdf_data.filename}"
        # return response
        return render_template("viewinvoice.html", pdf_data=pdf_data)
    else:
        return "PDF not found", 404
    
#This code working fine 
# @app.route("/viewdata/<pdf_id>")
# def view_data(pdf_id):
#     pdf_data = fs.find_one({"_id": ObjectId(pdf_id)})
#     pdf_text = pdf_data.metadata["text"]
#     print(pdf_text)
#     # Extract relevant information from the PDF text
#     parsed_data = {
#         "Invoice Number": get_field_value(pdf_text, "INVOICE#"),
#         "Invoice Number": get_field_value(pdf_text, "Invoice Number"),
#         "Company Name": get_field_value(pdf_text, "Company Name"),
#         "Customer Name": get_field_value(pdf_text, "Customer Name"),
#         "Customer Email ID": get_field_value(pdf_text, "Customer Email ID"),
#         "Phone No.": get_field_value(pdf_text, "Phone No."),
#         "Customer Address.": get_field_value(pdf_text, "Customer Address"),
#         "TOTAL": get_field_value(pdf_text, "TOTAL"),
#         "Total": get_field_value(pdf_text, "Total"),
#         "BILL TO ": get_field_value(pdf_text, "BILL TO "),
#         # Add more fields as needed
#     }
#     print(parsed_data)

#     return render_template('newviewdata.html', pdf_content=parsed_data)

# def get_field_value(pdf_text, field_name):
#     lines = pdf_text.split('\n')
#     for line in lines:
#         if field_name in line:
#             return line.split(field_name, 1)[1].strip()

@app.route("/viewdata/<pdf_id>")
def view_data(pdf_id):
    pdf_data = fs.find_one({"_id": ObjectId(pdf_id)})

    if pdf_data:
        pdf_text = pdf_data.metadata.get("text")
        parsed_data = parse_pdf_text(pdf_text)
        return render_template('newviewdata.html', pdf_content=parsed_data)
    else:
        return "PDF not found", 404

def parse_pdf_text(pdf_text):
    # Parsing logic based on the structure of the provided PDF texts
    parsed_data = {}

    # Common fields
    parsed_data["Invoice Number"] = get_field_value(pdf_text, "INVOICE#")
    parsed_data["Invoice Number"] = get_field_value(pdf_text, "Invoice Number#")
    parsed_data["Company Name"] = get_field_value(pdf_text, "Company Name")
    parsed_data["Customer Name"] = get_field_value(pdf_text, "Customer Name")
    parsed_data["Customer Email ID"] = get_field_value(pdf_text, "Customer Email ID")
    parsed_data["Phone No."] = get_field_value(pdf_text, "Phone No.")
    parsed_data["TOTAL"] = get_field_value(pdf_text, "TOTAL")
    parsed_data["Customer Address."] = get_field_value(pdf_text, "Customer Address.")
    parsed_data["BILL TO"] = get_field_value(pdf_text, "BILL TO")

    # Specific to each PDF
    if "LED T-Shirt" in pdf_text:
        parsed_data["No Items"] = "1"
        parsed_data["TOTAL"] = get_field_value(pdf_text, "Total ₹")

    return parsed_data

def get_field_value(pdf_text, field):
    # Extract field value based on a common pattern in the provided PDF texts
    start_index = pdf_text.find(field)
    if start_index != -1:
        end_index = pdf_text.find('\n', start_index)
        return pdf_text[start_index + len(field):end_index].strip()
    return None


@app.route("/delete/<pdf_id>")
def delete_entry(pdf_id):
    fs.delete(ObjectId(pdf_id))
    return redirect(url_for('get_all_data'))

def extract_pdf_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

def store_pdf_and_text(filename, text, pdf_file):
    pdf_id = fs.put(pdf_file, filename=filename, metadata={"text": text})
    return pdf_id

# @app.route('/upload', methods=['POST',"GET"])
# def upload():
#     # if 'pdf' not in request.files:
#     #     return redirect(request.url)
#     if request.method=="POST":
#         pdf_file = request.files['pdf']
#         # if pdf_file.filename == '':
#         #     return redirect(request.url)
#         if pdf_file:
#             pdf_text = extract_pdf_text(pdf_file)
#             store_pdf_and_text(pdf_file.filename, pdf_text, pdf_file)
#             return redirect(url_for('get_all_data', filename=pdf_file.filename))
#     return render_template("upload.html")
#PDF upload route
@app.route('/upload', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        pdf_file = request.files['pdf']
        if pdf_file:
            pdf_text = extract_pdf_text(pdf_file)
            store_pdf_and_text(pdf_file.filename, pdf_text, pdf_file)
            return redirect(url_for('get_all_data')) 
    return render_template("upload.html")
                           
# @app.route("/viewdata")
# def viewdata():
#     return render_template("viewdata.html")


if __name__=="__main__":
    app.run(debug=True)