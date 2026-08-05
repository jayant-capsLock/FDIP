import supabase from "../config/supabase.js"

export const downloadDocument= async (storagePath) => {
    const {data,error} = await supabase.storage.from("documents").download(storagePath);
    if (error){
        throw error;
    }
    const buffer = Buffer.from(await data.arrayBuffer());
    return buffer;
}