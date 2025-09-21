//if statement
/*
if(condition){
    //code to be executed if condition is true
    }else{  
    //code to be executed if condition is false
    }
*/
//Example 
// if(2==='2')
// {
//     console.log("It is equal");
    
// }


//Short hand notation:
const balance=1000;
if(balance>500) console.log("test"); 


//Switch statement
/*
switch(expression){
    case x: 
        //code block
        break;
    case y:
        //code block
        break;
    default:

        //code block

}
*/
//Example
const month="march";
switch(month)
{
    case "Jan":
        
        console.log("It is January");
        break;      
    case "Feb":
      console.log("It is February");
        break;
    case "march":
        console.log("It is March");
        break;
    default:
        console.log("It is not Jan, Feb or March");
}
