"""Synthetic PDF screens, generated locally without client material."""
from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject


def prototype_pdf():
    writer=PdfWriter()
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    for number in (1,2):
        page=writer.add_blank_page(width=720,height=540)
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        # Page 1 allows submission; page 2 contradicts the requirement with a photo gate.
        lines=[('FICTIONAL CLINIC | PROTOTYPE ONLY',40,490,12),('Report non-safety process feedback',40,440,24),('What slowed your task?',40,375,16),('Describe the issue...',55,325,14)]
        if number==1:lines += [('Photo (optional - add it later)',40,240,16),('Submit feedback',60,100,16)]
        else:lines += [('Photo required before you can submit',40,240,16),('Add photo to enable submission',60,100,16)]
        commands=['0.96 0.96 0.98 rg 0 0 720 540 re f','1 1 1 rg 40 285 640 65 re f','0.1 0.1 0.8 rg 40 80 380 52 re f']
        for text,x,y,size in lines:commands.append(f'0.15 0.15 0.18 rg BT /F1 {size} Tf {x} {y} Td ({text.replace(chr(40),chr(92)+chr(40)).replace(chr(41),chr(92)+chr(41))}) Tj ET')
        stream=DecodedStreamObject();stream.set_data('\n'.join(commands).encode());page[NameObject('/Contents')]=writer._add_object(stream)
    out=BytesIO();writer.write(out);return out.getvalue()

if __name__=='__main__':
    from pathlib import Path
    Path('/tmp/design-visual-build/fictional-clinic-prototype.pdf').write_bytes(prototype_pdf())
