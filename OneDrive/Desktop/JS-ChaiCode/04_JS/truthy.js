// const username=[2,3];
// if(username){
//     console.log("Condition is true");
// }   
// else{
//     console.log("Condition is false");
// }

/*
Falsy Values: 
1. false
2. 0 and -0
3. "" (empty string)
4. null
5. undefined
6. NaN

Truthy Values:
1. "0" (string with single zero)
2. " " (string with single space)
3. [] (empty array) 
4. {} (empty object)
5. function(){} (an empty function)
6. Any other number (positive or negative)
7.'false' (string with the text 'false')
*/

const name1=" ";
if(name1)
{
    console.log("Condition is true");
}

//Checking if object is empty or not
const obj1={};
if(Object.keys(obj1).length===0)
{
    console.log("Object is empty");
}
//Nullish Coalescing Operator (??)
//It returns the right-hand operand when the left-hand operand is null or undefined, otherwise it returns the left-hand operand.
const a=5??10;
console.log(a);
const b=null;
console.log(b??20);
