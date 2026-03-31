//%attributes = {"invisible":true}
var $startUpParams : Text
var $r:=Get database parameter(User param value; $startUpParams)

var $formName:=$startUpParams

// if file get form for name
If (Position("/"; $formName)>0)
	If (Position("form.4DForm"; $formName)>0)
		If (Position("Project/"; $formName)=1)
			$formName:=Try(Folder(fk database folder).file($formName).parent.name)
		Else 
			$formName:=Try(File($formName; fk posix path).parent.name)
		End if 
	End if 
End if 

// take the screenshot
var $screenshot : Picture
FORM SCREENSHOT($formName; $screenshot)
var $blob : Blob
PICTURE TO BLOB($screenshot; $blob; ".png")

// save the screenshot and log
var $formFolder:=Folder(fk database folder).folder("Project/Sources/Forms/"+$formName)
var $f:=$formFolder.file("form.png")
$f.setContent($blob)
LOG EVENT(Into system standard outputs; $f.path; Information message)

QUIT 4D